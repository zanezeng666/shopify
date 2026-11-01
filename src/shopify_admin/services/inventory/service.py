# -*- coding: utf-8 -*-
"""库存服务：位置同步 / 水位查询 / 策略引擎 / 应用到 Shopify。

渠道库存获取由 channels 层提供（InventorySource），本服务负责：
- 策略匹配（店铺×SKU 模式 → 渠道/比例/上下限）
- 计算目标值 → Shopify set_inventory_level 写入
- 全程留痕 inventory_sync_logs
"""
from __future__ import annotations

import time
from datetime import datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select

from shopify_admin.core.database import session_scope
from shopify_admin.core.exceptions import NotFoundError
from shopify_admin.models.inventory import (
    InventoryLevel, InventoryLocation, InventorySyncLog, InventorySyncPolicy,
)
from shopify_admin.models.product import ProductVariant
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.platforms.shopify.types import InventorySyncResult
from shopify_admin.services.stores.service import StoreService

# 策略缓存 TTL（秒）：批量同步场景下避免每 SKU 一次 DB 查询
_POLICY_CACHE_TTL = 60.0


class InventoryService:
    def __init__(self, store_service: StoreService | None = None):
        self._stores = store_service or StoreService()
        self._policy_cache: dict[int, tuple[float, list[InventorySyncPolicy]]] = {}

    # ------------------------------------------------------------------
    def sync_locations(self, store_id: int) -> dict:
        """同步 Shopify 发货位置。"""
        client = self._stores.get_client(store_id)
        try:
            locations = ShopifyRest(client).locations()
            with session_scope() as s:
                for loc in locations:
                    row = s.execute(
                        select(InventoryLocation).where(
                            InventoryLocation.store_id == store_id,
                            InventoryLocation.location_id == loc["id"],
                        )
                    ).scalar_one_or_none()
                    if row is None:
                        row = InventoryLocation(store_id=store_id, location_id=loc["id"])
                        s.add(row)
                    row.name = loc.get("name") or ""
                    row.is_active = bool(loc.get("active"))
                    row.address = loc.get("address")
                # 老系统主发货位置约定：第一条 active 位置为主
                primary = s.execute(
                    select(InventoryLocation).where(
                        InventoryLocation.store_id == store_id, InventoryLocation.is_primary.is_(True)
                    )
                ).scalar_one_or_none()
                if primary is None:
                    first = s.execute(
                        select(InventoryLocation).where(
                            InventoryLocation.store_id == store_id, InventoryLocation.is_active.is_(True)
                        ).order_by(InventoryLocation.id)
                    ).scalars().first()
                    if first is not None:
                        first.is_primary = True
            return {"locations": len(locations)}
        finally:
            client.close()

    def get_primary_location(self, store_id: int) -> InventoryLocation | None:
        with session_scope() as s:
            loc = s.execute(
                select(InventoryLocation).where(
                    InventoryLocation.store_id == store_id, InventoryLocation.is_primary.is_(True)
                )
            ).scalar_one_or_none()
            return loc

    # ------------------------------------------------------------------
    def list_levels(self, store_id: int, sku: str | None = None, page: int = 1, page_size: int = 50) -> dict:
        with session_scope() as s:
            stmt = select(InventoryLevel).where(InventoryLevel.store_id == store_id)
            count_stmt = select(func.count(InventoryLevel.id)).where(InventoryLevel.store_id == store_id)
            if sku:
                stmt = stmt.where(InventoryLevel.sku.like(f"%{sku}%"))
                count_stmt = count_stmt.where(InventoryLevel.sku.like(f"%{sku}%"))
            total = s.execute(count_stmt).scalar() or 0
            rows = (
                s.execute(stmt.order_by(InventoryLevel.sku).offset((page - 1) * page_size).limit(page_size))
                .scalars()
                .all()
            )
            return {
                "total": total,
                "items": [
                    {
                        "sku": r.sku, "cs_id": r.cs_id, "channel": r.channel,
                        "inventory_item_id": r.inventory_item_id, "location_id": r.location_id,
                        "available": r.available,
                        "synced_at": r.synced_at.isoformat() if r.synced_at else None,
                    }
                    for r in rows
                ],
            }

    # ------------------------------------------------------------------
    # 策略管理
    # ------------------------------------------------------------------
    def list_policies(self, store_id: int) -> list[dict]:
        with session_scope() as s:
            rows = (
                s.execute(
                    select(InventorySyncPolicy)
                    .where(InventorySyncPolicy.store_id == store_id)
                    .order_by(InventorySyncPolicy.priority)
                )
                .scalars()
                .all()
            )
            return [self._policy_dict(r) for r in rows]

    def upsert_policy(self, store_id: int, sku_pattern: str, **kwargs) -> dict:
        with session_scope() as s:
            pol = s.execute(
                select(InventorySyncPolicy).where(
                    InventorySyncPolicy.store_id == store_id, InventorySyncPolicy.sku_pattern == sku_pattern
                )
            ).scalar_one_or_none()
            if pol is None:
                pol = InventorySyncPolicy(store_id=store_id, sku_pattern=sku_pattern)
                s.add(pol)
            for k in ("channel", "ratio", "min_qty", "max_qty", "priority", "enabled", "note"):
                if k in kwargs and kwargs[k] is not None:
                    setattr(pol, k, kwargs[k])
            s.flush()
            self._policy_cache.pop(store_id, None)
            return self._policy_dict(pol)

    def _policies(self, store_id: int) -> list[InventorySyncPolicy]:
        """启用策略列表（进程内 60s 缓存：批量同步防每 SKU 一次 DB 查询）。"""
        hit = self._policy_cache.get(store_id)
        if hit is not None and (time.time() - hit[0]) < _POLICY_CACHE_TTL:
            return hit[1]
        with session_scope() as s:
            rows = s.execute(
                select(InventorySyncPolicy).where(
                    InventorySyncPolicy.store_id == store_id, InventorySyncPolicy.enabled.is_(True)
                ).order_by(InventorySyncPolicy.priority)
            ).scalars().all()
        self._policy_cache[store_id] = (time.time(), rows)
        return rows

    def match_policy(self, store_id: int, sku: str) -> InventorySyncPolicy | None:
        """策略匹配：精确命中 > 前缀通配（BM-%）；priority 小者优先。"""
        policies = self._policies(store_id)
        exact = [p for p in policies if p.sku_pattern == sku]
        if exact:
            return exact[0]
        for p in policies:
            if p.sku_pattern.endswith("%") and sku.startswith(p.sku_pattern[:-1]):
                return p
        return None

    # ------------------------------------------------------------------
    # 核心：应用库存值到 Shopify
    # ------------------------------------------------------------------
    def apply_channel_stock(
        self,
        store_id: int,
        channel_stocks: list[dict],
        dry_run: bool = False,
    ) -> InventorySyncResult:
        """把渠道库存应用到 Shopify。

        channel_stocks: [{"sku", "available", "cs_id"?}]
        流程：SKU → 变体(inventory_item_id) → 策略计算 → set_inventory_level → 日志。
        """
        result = InventorySyncResult(store_id=store_id)
        location = self.get_primary_location(store_id)
        if location is None:
            logger.warning("[inventory] 无主发货位置，先执行 sync_locations")
            self.sync_locations(store_id)
            location = self.get_primary_location(store_id)
            if location is None:
                raise NotFoundError(f"店铺 {store_id} 无可用发货位置")

        client = self._stores.get_client(store_id) if not dry_run else None
        rest = ShopifyRest(client) if client else None
        try:
            for cs in channel_stocks:
                sku = cs.get("sku", "")
                raw_qty = int(cs.get("available") or 0)
                result.checked += 1
                try:
                    target = self._compute_target(store_id, sku, raw_qty)
                    with session_scope() as s:
                        var = s.execute(
                            select(ProductVariant).where(
                                ProductVariant.store_id == store_id, ProductVariant.sku == sku
                            ).limit(1)
                        ).scalar_one_or_none()
                    if var is None or var.inventory_item_id is None:
                        self._log(store_id, sku, cs.get("cs_id", ""), "", raw_qty, target, None, False, "变体未同步或无 inventory_item_id")
                        result.failed += 1
                        continue

                    with session_scope() as s:
                        level = s.execute(
                            select(InventoryLevel).where(
                                InventoryLevel.store_id == store_id,
                                InventoryLevel.inventory_item_id == var.inventory_item_id,
                                InventoryLevel.location_id == location.location_id,
                            )
                        ).scalar_one_or_none()
                    old = level.available if level else None

                    if target == old:
                        result.unchanged += 1
                        self._log(store_id, sku, cs.get("cs_id", ""), cs.get("channel", ""), old, target, target, True, "unchanged")
                        continue

                    applied = None
                    if not dry_run:
                        assert rest is not None
                        rest.set_inventory_level(var.inventory_item_id, location.location_id, target)
                        applied = target
                        self._cache_level(store_id, sku, var.inventory_item_id, location.location_id, target, cs)
                    result.updated += 1
                    self._log(store_id, sku, cs.get("cs_id", ""), cs.get("channel", ""), old, target, applied, True, "ok")
                except Exception as e:
                    result.failed += 1
                    self._log(store_id, sku, cs.get("cs_id", ""), cs.get("channel", ""), None, None, None, False, str(e)[:300])
                    logger.warning(f"[inventory] 同步失败 sku={sku}: {e}")
            return result
        finally:
            if client:
                client.close()

    def diff_channel_stock(self, store_id: int, channel_stocks: list[dict]) -> dict:
        """预筛目标水位与本地缓存不一致（或无缓存）的 SKU。

        定时任务限流用：本地先算 diff，只把"真变了"的 SKU 交给
        apply_channel_stock 推 Shopify，避免每轮全量打平台 API。
        """
        with session_scope() as s:
            levels = {
                sku: available
                for sku, available in s.execute(
                    select(InventoryLevel.sku, InventoryLevel.available).where(
                        InventoryLevel.store_id == store_id
                    )
                )
            }
        changed: list[dict] = []
        unchanged = 0
        for cs in channel_stocks:
            sku = cs.get("sku", "")
            try:
                raw_qty = int(cs.get("available") or 0)
            except (TypeError, ValueError):
                raw_qty = 0
            target = self._compute_target(store_id, sku, raw_qty)
            if levels.get(sku) == target:
                unchanged += 1
            else:
                changed.append(cs)
        return {"changed": changed, "unchanged": unchanged, "cached": len(levels)}

    def _compute_target(self, store_id: int, sku: str, raw_qty: int) -> int:
        """策略引擎：比例缩放 + 上下限钳位。"""
        policy = self.match_policy(store_id, sku)
        target = raw_qty
        channel = ""
        if policy is not None:
            ratio = Decimal(str(policy.ratio)) if policy.ratio else Decimal("1.00")
            target = int(raw_qty * ratio)
            target = max(target, policy.min_qty or 0)
            if policy.max_qty and policy.max_qty > 0:
                target = min(target, policy.max_qty)
            channel = policy.channel
        _ = channel  # 预留多渠道策略
        return max(target, 0)

    def _cache_level(self, store_id, sku, inventory_item_id, location_id, available, cs: dict) -> None:
        with session_scope() as s:
            level = s.execute(
                select(InventoryLevel).where(
                    InventoryLevel.store_id == store_id,
                    InventoryLevel.inventory_item_id == inventory_item_id,
                    InventoryLevel.location_id == location_id,
                )
            ).scalar_one_or_none()
            if level is None:
                level = InventoryLevel(
                    store_id=store_id, inventory_item_id=inventory_item_id, location_id=location_id
                )
                s.add(level)
            level.sku = sku
            level.available = available
            level.cs_id = cs.get("cs_id", "")
            level.channel = cs.get("channel", "")
            level.synced_at = datetime.now()

    @staticmethod
    def _log(store_id, sku, cs_id, channel, old, new, applied, success, message) -> None:
        try:
            with session_scope() as s:
                s.add(
                    InventorySyncLog(
                        store_id=store_id, sku=sku, cs_id=cs_id or "", channel=channel or "",
                        old_qty=old, new_qty=new, applied_qty=applied,
                        success=success, message=message,
                    )
                )
        except Exception as e:  # 日志失败不阻断同步
            logger.warning(f"[inventory] 日志写入失败: {e}")

    def list_sync_logs(self, store_id: int, limit: int = 100) -> list[dict]:
        with session_scope() as s:
            rows = (
                s.execute(
                    select(InventorySyncLog)
                    .where(InventorySyncLog.store_id == store_id)
                    .order_by(InventorySyncLog.synced_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [
                {
                    "sku": r.sku, "cs_id": r.cs_id, "channel": r.channel,
                    "old_qty": r.old_qty, "new_qty": r.new_qty, "applied_qty": r.applied_qty,
                    "success": r.success, "message": r.message,
                    "synced_at": r.synced_at.isoformat() if r.synced_at else None,
                }
                for r in rows
            ]

    def low_stock(self, store_id: int, threshold: int = 5) -> list[dict]:
        """低库存预警（本地水位 <= 阈值）。"""
        with session_scope() as s:
            rows = s.execute(
                select(InventoryLevel).where(
                    InventoryLevel.store_id == store_id, InventoryLevel.available <= threshold
                ).order_by(InventoryLevel.available)
            ).scalars().all()
            return [{"sku": r.sku, "available": r.available, "cs_id": r.cs_id, "channel": r.channel} for r in rows]

    # ------------------------------------------------------------------
    @staticmethod
    def _policy_dict(p: InventorySyncPolicy) -> dict:
        return {
            "id": p.id, "store_id": p.store_id, "sku_pattern": p.sku_pattern,
            "channel": p.channel, "ratio": float(p.ratio) if p.ratio else 1.0,
            "min_qty": p.min_qty, "max_qty": p.max_qty, "priority": p.priority,
            "enabled": p.enabled, "note": p.note,
        }
