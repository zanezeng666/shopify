# -*- coding: utf-8 -*-
"""订单域：订单 / 订单行项。

设计要点：
- local_status 为本系统履约状态机（与 Shopify fulfillment_status 独立）
- shopify_created_at 为增量拉单游标
- shipping_address/customer 等低频只读字段存 JSON
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from shopify_admin.models.base import Base, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("store_id", "shopify_order_id", name="uq_orders_store_soid"),
        Index("ix_orders_store_created", "store_id", "shopify_created_at"),
        Index("ix_orders_local_status", "local_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    shopify_order_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 订单 ID")
    name: Mapped[str] = mapped_column(String(32), default="", comment="订单号如 #1001")
    order_number: Mapped[int] = mapped_column(Integer, default=0)
    email: Mapped[str] = mapped_column(String(255), default="")
    phone: Mapped[str] = mapped_column(String(64), default="")
    financial_status: Mapped[str] = mapped_column(String(32), default="", comment="pending/authorized/paid/refunded/voided")
    fulfillment_status: Mapped[str] = mapped_column(String(32), default="unfulfilled", comment="Shopify 履约状态")
    # 本系统履约状态机: pending(待处理) -> routed(已分仓) -> submitted(已渠道下单)
    #   -> shipped(已发货) -> completed(完成) / failed(异常) / cancelled(取消)
    local_status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    channel: Mapped[str] = mapped_column(String(16), default="", comment="分仓结果: cs / fastrite / manual")
    currency: Mapped[str] = mapped_column(String(8), default="")
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    subtotal_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    total_tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    total_discounts: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    shipping_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    tags: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    shipping_address: Mapped[dict | None] = mapped_column(JSON, default=None)
    billing_address: Mapped[dict | None] = mapped_column(JSON, default=None)
    customer: Mapped[dict | None] = mapped_column(JSON, default=None)
    is_test: Mapped[bool] = mapped_column(default=False, comment="Shopify 测试单")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    shopify_created_at: Mapped[datetime | None] = mapped_column(DateTime, default=None, comment="拉单游标")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint("order_id", "shopify_line_item_id", name="uq_items_order_line"),
        Index("ix_items_order", "order_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    shopify_line_item_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify 行项 ID")
    shopify_product_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    shopify_variant_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    inventory_item_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    title: Mapped[str] = mapped_column(String(512), default="")
    sku: Mapped[str] = mapped_column(String(128), default="", index=True, comment="行项 SKU（履约映射键）")
    cs_id: Mapped[str] = mapped_column(String(64), default="", comment="映射的 CS 产品号")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    fulfillable_quantity: Mapped[int] = mapped_column(Integer, default=1)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    total_discount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    grams: Mapped[int] = mapped_column(Integer, default=0)
    properties: Mapped[dict | None] = mapped_column(JSON, default=None)
