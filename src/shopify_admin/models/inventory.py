# -*- coding: utf-8 -*-
"""库存域：位置 / 库存水位 / 同步日志 / 同步策略。

同步链路：渠道库存（CS via bmai / FastRite）→ 策略引擎 → Shopify 位置库存。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from shopify_admin.models.base import Base, TimestampMixin


class InventoryLocation(Base, TimestampMixin):
    __tablename__ = "inventory_locations"
    __table_args__ = (UniqueConstraint("store_id", "location_id", name="uq_locations_store_loc"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    location_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify location ID")
    name: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, comment="主发货位置")
    address: Mapped[dict | None] = mapped_column(JSON, default=None)


class InventoryLevel(Base, TimestampMixin):
    """库存水位（本地缓存，最近值）。"""

    __tablename__ = "inventory_levels"
    __table_args__ = (
        UniqueConstraint("store_id", "inventory_item_id", "location_id", name="uq_levels_item_loc"),
        Index("ix_levels_store_sku", "store_id", "sku"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    sku: Mapped[str] = mapped_column(String(128), default="", comment="冗余 SKU 便于查询")
    inventory_item_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 库存项 ID")
    location_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 位置 ID")
    available: Mapped[int] = mapped_column(Integer, default=0, comment="可用库存")
    cs_id: Mapped[str] = mapped_column(String(64), default="", comment="映射 CS 产品号")
    channel: Mapped[str] = mapped_column(String(16), default="", comment="库存来源渠道 cs/fastrite")
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="最近同步时间")


class InventorySyncLog(Base):
    """单次库存同步明细（审计 + 排障）。"""

    __tablename__ = "inventory_sync_logs"
    __table_args__ = (Index("ix_sync_logs_store_time", "store_id", "synced_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"))
    sku: Mapped[str] = mapped_column(String(128), default="")
    cs_id: Mapped[str] = mapped_column(String(64), default="")
    channel: Mapped[str] = mapped_column(String(16), default="")
    old_qty: Mapped[int | None] = mapped_column(Integer, default=None, comment="Shopify 侧旧值")
    new_qty: Mapped[int | None] = mapped_column(Integer, default=None, comment="渠道计算值")
    applied_qty: Mapped[int | None] = mapped_column(Integer, default=None, comment="实际写入值")
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    message: Mapped[str] = mapped_column(Text, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class InventorySyncPolicy(Base, TimestampMixin):
    """库存同步策略（按店铺×SKU 模式差异化：渠道选择/折扣系数/上下限）。"""

    __tablename__ = "inventory_sync_policies"
    __table_args__ = (
        UniqueConstraint("store_id", "sku_pattern", name="uq_policies_store_pattern"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    sku_pattern: Mapped[str] = mapped_column(String(128), comment="SKU 精确值或前缀通配（如 BM-%）")
    channel: Mapped[str] = mapped_column(String(16), default="cs", comment="优先库存来源 cs/fastrite")
    ratio: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1.00"), comment="同步比例（安全库存打折）")
    min_qty: Mapped[int] = mapped_column(Integer, default=0, comment="同步下限保护")
    max_qty: Mapped[int] = mapped_column(Integer, default=0, comment="同步上限（0=不限制）")
    priority: Mapped[int] = mapped_column(Integer, default=100, comment="多策略命中时取优先级最小")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(255), default="")
