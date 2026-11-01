# -*- coding: utf-8 -*-
"""履约编排服务：分仓路由 -> 渠道下单 -> 状态轮询 -> 跟踪号回传。

状态机（orders.local_status）:
    pending -> routed -> submitted -> shipped -> completed
                                  -> failed / cancelled

路由策略（对齐老系统，Shopify 平台实现）:
    1. 行项 SKU 在 FastRite 海外仓有库存 → fastrite（仓库优先）
    2. CS 供应商有库存 → cs（兜底）
    3. 均无 → manual（人工处理，标记异常）
    force_channel 可人工指定。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select

from shopify_admin.channels.base import (
    Address, ChannelOrderRef, FulfillmentLine, FulfillmentRequest, Parcel,
)
from shopify_admin.channels.registry import available_channels, get_channel
from shopify_admin.core.database import session_scope
from shopify_admin.core.exceptions import ChannelError, NotFoundError, RouteError
from shopify_admin.models.fulfillment import FulfillmentOrder
from shopify_admin.models.order import Order, OrderItem
from shopify_admin.models.store import Store
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService


class FulfillmentService:
    def __init__(self, store_service: StoreService | None = None):
        self._stores = store_service or StoreService()

    # ==================================================================
    # 分仓路由
    # ==================================================================
    def route_order(self, order_id: int, force_channel: str | None = None, dry_run: bool = False) -> dict:
        """订单分仓路由（按行项粒度路由，整单允许混合渠道）。"""
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                raise NotFoundError(f"订单不存在: {order_id}")
            items = s.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
            if not items:
                raise RouteError("订单无行项，无法路由")

            if force_channel:
                if force_channel not in available_channels() + ["manual"]:
                    raise RouteError(f"未知渠道: {force_channel}")
                decisions = [
                    {"item_id": it.id, "sku": it.sku, "channel": force_channel, "reason": "manual"}
                    for it in items
                ]
            else:
                decisions = self._route_items(items, order)

            if dry_run:
                return {"order_id": order_id, "dry_run": True, "decisions": decisions}

            order.channel = ",".join(sorted({d["channel"] for d in decisions}))
            order.local_status = "routed"
            for d in decisions:
                fo = s.execute(
                    select(FulfillmentOrder).where(
                        FulfillmentOrder.order_id == order_id,
                        FulfillmentOrder.order_item_id == d["item_id"],
                        FulfillmentOrder.channel == d["channel"],
                    )
                ).scalar_one_or_none()
                if fo is None:
                    s.add(
                        FulfillmentOrder(
                            store_id=order.store_id, order_id=order_id, order_item_id=d["item_id"],
                            channel=d["channel"], route_reason=d["reason"], status="pending",
                        )
                    )
                else:
                    fo.route_reason = d["reason"]

            logger.info(f"[fulfillment] 分仓完成 order={order_id} -> {order.channel}")
            return {"order_id": order_id, "decisions": decisions}

    @staticmethod
    def _route_items(items: list[OrderItem], order: Order) -> list[dict]:
        """逐行项路由：FastRite 优先（目的国在仓），CS 兜底。"""
        decisions = []
        dest_country = (order.shipping_address or {}).get("country_code", "") if order.shipping_address else ""
        for it in items:
            sku = it.sku
            channel, reason = "manual", "no_stock"
            if sku:
                try:
                    fr = get_channel("fastrite").get_inventory(sku)
                    if fr.available >= it.quantity and dest_country.upper() in fr.raw.get("countries", ["US", "CA", "GB", "DE", "AU"]):
                        channel, reason = "fastrite", "warehouse_first"
                except Exception as e:
                    logger.debug(f"[fulfillment] FastRite 库存查询失败 sku={sku}: {e}")
                if channel == "manual":
                    try:
                        cs = get_channel("cs").get_inventory(sku)
                        if cs.available >= it.quantity:
                            channel, reason = "cs", "cs_fallback"
                    except Exception as e:
                        logger.debug(f"[fulfillment] CS 库存查询失败 sku={sku}: {e}")
            decisions.append({"item_id": it.id, "sku": sku, "channel": channel, "reason": reason})
        return decisions

    # ==================================================================
    # 渠道下单
    # ==================================================================
    def submit_order(self, order_id: int, channel: str | None = None) -> dict:
        """对已路由订单执行渠道下单（fulfillment_orders -> 渠道）。

        - fastrite：同渠道行项合并一张出库单
        - cs：逐行项单独代发（CIM dropship 单行项语义），每行带 order_item_id 去重
        """
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                raise NotFoundError(f"订单不存在: {order_id}")
            if order.local_status not in ("pending", "routed", "failed"):
                raise ChannelError(f"订单状态 {order.local_status} 不可下单")
            store_id = order.store_id
            store = s.get(Store, store_id)
            fos = s.execute(
                select(FulfillmentOrder).where(FulfillmentOrder.order_id == order_id)
            ).scalars().all()
            ship_addr = order.shipping_address or {}
            order_name = order.name or str(order.shopify_order_id)
            store_ctx = {
                "rcustomerno": str(store.rcustomerno or "") if store else "",
                "username": store.username if store else "",
                "main_ship_by": store.main_ship_by if store else "auto",
            }

        # 地址转换
        address = Address(
            name=ship_addr.get("name", ""),
            phone=ship_addr.get("phone", ""),
            country_code=ship_addr.get("country_code", ""),
            province=ship_addr.get("province", ""),
            city=ship_addr.get("city", ""),
            zip=ship_addr.get("zip", ""),
            address1=ship_addr.get("address1", ""),
            address2=ship_addr.get("address2", ""),
        )

        submitted: list[dict] = []
        failed: list[dict] = []
        # 按渠道分组行项
        by_channel: dict[str, list[FulfillmentOrder]] = {}
        for fo in fos:
            if fo.status not in ("pending", "failed"):
                continue
            if channel and fo.channel != channel:
                continue
            by_channel.setdefault(fo.channel, []).append(fo)

        def _load_lines(group: list[FulfillmentOrder]) -> tuple[list[FulfillmentLine], list[int]]:
            lines, fo_ids, grams = [], [], 0
            with session_scope() as s:
                for fo in group:
                    it = s.get(OrderItem, fo.order_item_id) if fo.order_item_id else None
                    if it is None:
                        continue
                    lines.append(
                        FulfillmentLine(
                            sku=it.sku, quantity=it.quantity, cs_id=it.cs_id,
                            order_item_id=str(it.shopify_line_item_id or ""),
                        )
                    )
                    fo_ids.append(fo.id)
                    grams += (it.grams or 0) * it.quantity
            return lines, fo_ids

        def _mark(ids: list[int], ok: bool, ref=None, error: str = "") -> None:
            with session_scope() as s:
                for fid in ids:
                    fo = s.get(FulfillmentOrder, fid)
                    if fo is None:
                        continue
                    if ok:
                        fo.status = "submitted"
                        fo.channel_order_ref = ref.order_id
                        fo.cs_order_id = ref.order_id if fo.channel == "cs" else ""
                        fo.submitted_at = datetime.now()
                        fo.raw = (fo.raw or {}) | {"submit": ref.raw}
                    else:
                        fo.status = "failed"
                        fo.error_message = error[:500]
                        fo.exception_type = _classify_exception(Exception(error))
                s.get(Order, order_id).local_status = "submitted" if ok else "failed"

        for ch_name, ch_fos in by_channel.items():
            if ch_name == "manual":
                continue
            ch = get_channel(
                ch_name,
                rcustomerno=store_ctx["rcustomerno"],
                store_name=store_ctx["username"],
            )
            lines, fo_ids = _load_lines(ch_fos)
            if not lines:
                continue
            # CS 逐行项提交；fastrite 合并一单
            batches = [[ln] for ln in lines] if ch_name == "cs" else [lines]
            for i, batch in enumerate(batches):
                ids = fo_ids if len(batches) == 1 else [fo_ids[i]]
                req = FulfillmentRequest(
                    order_ref=order_name,
                    lines=batch,
                    ship_to=address,
                    parcel=Parcel(items=[{"sku": l.sku, "qty": l.quantity} for l in batch]),
                    extra={"main_ship_by": store_ctx["main_ship_by"]},
                )
                try:
                    ref = ch.submit_order(req)
                    _mark(ids, ok=True, ref=ref)
                    submitted.append({"channel": ch_name, "channel_order_ref": ref.order_id, "lines": len(batch)})
                    logger.info(f"[fulfillment] 下单成功 order={order_id} {ch_name} -> {ref.order_id}")
                except Exception as e:
                    _mark(ids, ok=False, error=str(e))
                    failed.append({"channel": ch_name, "error": str(e)[:300]})
                    logger.error(f"[fulfillment] 下单失败 order={order_id} {ch_name}: {e}")

        return {"order_id": order_id, "submitted": submitted, "failed": failed}

    # ==================================================================
    # 状态轮询 + 跟踪号回传
    # ==================================================================
    def poll_channel_status(self, store_id: int | None = None, max_items: int = 100) -> dict:
        """轮询已下单履约单的渠道状态；有跟踪号自动回传 Shopify。"""
        with session_scope() as s:
            stmt = (
                select(FulfillmentOrder)
                .where(FulfillmentOrder.status.in_(["submitted", "processing", "pending"]))
                .order_by(FulfillmentOrder.submitted_at)
                .limit(max_items)
            )
            if store_id:
                stmt = stmt.where(FulfillmentOrder.store_id == store_id)
            fos = s.execute(stmt).scalars().all()
            targets = [
                {
                    "id": f.id, "channel": f.channel, "ref": f.channel_order_ref,
                    "order_id": f.order_id,
                    "order_name": (
                        s.execute(select(Order.name).where(Order.id == f.order_id)).scalar_one_or_none()
                        or ""
                    ),
                }
                for f in fos
            ]

        updated, shipped, completed, errors = 0, 0, 0, 0
        for t in targets:
            if not t["ref"]:
                continue
            try:
                ch = get_channel(t["channel"])
                status = ch.get_status(ChannelOrderRef(
                    channel=t["channel"], order_id=t["ref"], third_order_no=t["order_name"],
                ))
                updated += 1
                if status.status == "shipped" and status.tracking_number:
                    shipped += 1
                    self.push_tracking(t["id"], status.tracking_number, status.tracking_company, status.tracking_url)
                elif status.status == "completed":
                    completed += 1
                    with session_scope() as s:
                        fo = s.get(FulfillmentOrder, t["id"])
                        fo.status = "completed"
                        fo.completed_at = datetime.now()
                elif status.status in ("failed", "cancelled"):
                    errors += 1
                    with session_scope() as s:
                        fo = s.get(FulfillmentOrder, t["id"])
                        fo.status = status.status
                        fo.error_message = status.error_message or status.status
            except Exception as e:
                logger.debug(f"[fulfillment] 轮询失败 fo={t['id']}: {e}")
        return {"checked": len(targets), "updated": updated, "shipped_pushed": shipped, "completed": completed, "errors": errors}

    def push_tracking(
        self, fulfillment_order_id: int, tracking_number: str,
        tracking_company: str = "", tracking_url: str = "",
    ) -> dict:
        """跟踪号回传 Shopify（创建 fulfillment），更新本地状态。"""
        with session_scope() as s:
            fo = s.get(FulfillmentOrder, fulfillment_order_id)
            if fo is None:
                raise NotFoundError(f"履约单不存在: {fulfillment_order_id}")
            if fo.shopify_fulfillment_id:
                return {"ok": False, "message": "已回传过", "shopify_fulfillment_id": fo.shopify_fulfillment_id}
            order = s.get(Order, fo.order_id)
            store_id = order.store_id
            shopify_order_id = order.shopify_order_id
            line_item_id = None
            if fo.order_item_id:
                it = s.get(OrderItem, fo.order_item_id)
                line_item_id = it.shopify_line_item_id if it else None

        client = self._stores.get_client(store_id)
        try:
            line_items = [{"id": line_item_id}] if line_item_id else None
            fulfillment = ShopifyRest(client).create_fulfillment(
                shopify_order_id, tracking_number, tracking_company, tracking_url, line_items
            )
            with session_scope() as s:
                fo = s.get(FulfillmentOrder, fulfillment_order_id)
                fo.tracking_number = tracking_number
                fo.tracking_company = tracking_company
                fo.tracking_url = tracking_url
                fo.shopify_fulfillment_id = fulfillment.get("id")
                fo.status = "shipped"
                fo.shipped_at = datetime.now()
                order = s.get(Order, fo.order_id)
                # 整单完成判定：所有履约单均 shipped/completed
                all_done = not s.execute(
                    select(func.count(FulfillmentOrder.id)).where(
                        FulfillmentOrder.order_id == fo.order_id,
                        FulfillmentOrder.status.notin_(["shipped", "completed", "cancelled"]),
                    )
                ).scalar()
                order.local_status = "shipped" if not all_done else "completed"
                order.fulfillment_status = fulfillment.get("status") or order.fulfillment_status
            logger.info(f"[fulfillment] 跟踪号回传 fo={fulfillment_order_id} -> {tracking_number}")
            return {"ok": True, "shopify_fulfillment_id": fulfillment.get("id"), "tracking_number": tracking_number}
        finally:
            client.close()

    # ==================================================================
    # 查询 / 异常处理
    # ==================================================================
    def list_fulfillments(
        self,
        store_id: int | None = None,
        order_id: int | None = None,
        status: str | None = None,
        channel: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        with session_scope() as s:
            stmt = select(FulfillmentOrder)
            count_stmt = select(func.count(FulfillmentOrder.id))
            for field, val in (("store_id", store_id), ("order_id", order_id), ("status", status), ("channel", channel)):
                if val:
                    stmt = stmt.where(getattr(FulfillmentOrder, field) == val)
                    count_stmt = count_stmt.where(getattr(FulfillmentOrder, field) == val)
            total = s.execute(count_stmt).scalar() or 0
            rows = (
                s.execute(stmt.order_by(FulfillmentOrder.id.desc()).offset((page - 1) * page_size).limit(page_size))
                .scalars()
                .all()
            )
            return {
                "total": total,
                "items": [
                    {
                        "id": f.id, "order_id": f.order_id, "store_id": f.store_id,
                        "channel": f.channel, "status": f.status, "route_reason": f.route_reason,
                        "cs_order_id": f.cs_order_id, "channel_order_ref": f.channel_order_ref,
                        "tracking_number": f.tracking_number, "tracking_url": f.tracking_url,
                        "shopify_fulfillment_id": f.shopify_fulfillment_id,
                        "exception_type": f.exception_type, "error_message": f.error_message,
                        "submitted_at": f.submitted_at.isoformat() if f.submitted_at else None,
                    }
                    for f in rows
                ],
            }

    def mark_exception(self, fulfillment_order_id: int, exception_type: str, note: str = "") -> dict:
        """异常标记（余额不足/停产/物流不可达/其他）。"""
        with session_scope() as s:
            fo = s.get(FulfillmentOrder, fulfillment_order_id)
            if fo is None:
                raise NotFoundError(f"履约单不存在: {fulfillment_order_id}")
            fo.exception_type = exception_type
            fo.error_message = note or fo.error_message
            fo.status = "failed"
            s.get(Order, fo.order_id).local_status = "failed"
            return {"ok": True, "id": fulfillment_order_id, "exception_type": exception_type}


def _classify_exception(e: Exception) -> str:
    """渠道异常归类（对齐老系统异常分类）。"""
    text = str(e).lower()
    if "balance" in text or "余额" in text:
        return "insufficient_balance"
    if "stop" in text or "停产" in text or "eol" in text:
        return "product_discontinued"
    if "unreachable" in text or "不可达" in text or "remote" in text:
        return "logistics_unreachable"
    return "other"
