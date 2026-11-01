# -*- coding: utf-8 -*-
"""履约域：渠道履约单（分仓结果 + 渠道下单 + 跟踪号回传状态机）。

去重单一事实源是 bmai 管的 cs_new.order_records（platform+order_id+order_item_id 唯一），
本表记录本系统视角的履约全过程（含 FastRite 渠道）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from shopify_admin.models.base import Base, TimestampMixin


class FulfillmentOrder(Base, TimestampMixin):
    __tablename__ = "fulfillment_orders"
    __table_args__ = (
        UniqueConstraint("order_id", "order_item_id", "channel", name="uq_fo_order_item_channel"),
        Index("ix_fo_status", "status"),
        Index("ix_fo_channel_ref", "channel", "channel_order_ref"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, comment="本地订单 ID")
    order_item_id: Mapped[int | None] = mapped_column(ForeignKey("order_items.id"), default=None, comment="空=整单履约")
    channel: Mapped[str] = mapped_column(String(16), comment="cs / fastrite")
    route_reason: Mapped[str] = mapped_column(String(64), default="", comment="分仓依据: warehouse_first/cs_fallback/manual/policy")
    # 状态机: pending(待提交) -> submitted(渠道已接单) -> processing -> shipped(已发货)
    #   -> completed(跟踪号已回传) / failed(异常) / cancelled
    status: Mapped[str] = mapped_column(String(32), default="pending")
    cs_order_id: Mapped[str] = mapped_column(String(64), default="", comment="CS 订单号")
    channel_order_ref: Mapped[str] = mapped_column(String(128), default="", comment="渠道侧单号（FastRite）")
    shopify_fulfillment_id: Mapped[int | None] = mapped_column(BigInteger, default=None, comment="回传后的 Shopify fulfillment ID")
    tracking_number: Mapped[str] = mapped_column(String(128), default="")
    tracking_company: Mapped[str] = mapped_column(String(128), default="")
    tracking_url: Mapped[str] = mapped_column(String(512), default="")
    exception_type: Mapped[str] = mapped_column(String(64), default="", comment="余额不足/停产/物流不可达/其他")
    error_message: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None, comment="渠道下单原始响应")
