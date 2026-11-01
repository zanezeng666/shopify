# -*- coding: utf-8 -*-
"""财务域：payout / 交易流水 / 订单成本。

与 bmai 的 cs_transaction_record（CS 侧流水）互不重复——本组只管 Shopify 侧资金与利润核算。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer,
    Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from shopify_admin.models.base import Base, TimestampMixin


class Payout(Base, TimestampMixin):
    """Shopify 结算（Shopify Payments 打款）。"""

    __tablename__ = "payouts"
    __table_args__ = (
        UniqueConstraint("store_id", "payout_id", name="uq_payouts_store_pid"),
        Index("ix_payouts_store_date", "store_id", "payout_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    payout_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify payout ID")
    status: Mapped[str] = mapped_column(String(32), default="", comment="scheduled/in_transit/paid/canceled/failed")
    payout_date: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    currency: Mapped[str] = mapped_column(String(8), default="")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)


class Transaction(Base, TimestampMixin):
    """Shopify 订单交易（sale/refund/fee 等明细，对账数据源）。"""

    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("store_id", "transaction_id", name="uq_txns_store_tid"),
        Index("ix_txns_store_order", "store_id", "shopify_order_id"),
        Index("ix_txns_store_processed", "store_id", "processed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    transaction_id: Mapped[int] = mapped_column(BigInteger, comment="Shopify transaction ID")
    shopify_order_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    kind: Mapped[str] = mapped_column(String(32), default="", comment="sale/capture/refund/void/fee/adjustment")
    gateway: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="")
    currency: Mapped[str] = mapped_column(String(8), default="")
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    net: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    raw: Mapped[dict | None] = mapped_column(JSON, default=None)


class OrderCost(Base, TimestampMixin):
    """订单成本核算：收入 - 货品成本 - 运费 = 利润（按行项 SKU 粒度）。"""

    __tablename__ = "order_costs"
    __table_args__ = (UniqueConstraint("order_id", "sku", name="uq_costs_order_sku"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, comment="本地订单 ID")
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id"), index=True)
    sku: Mapped[str] = mapped_column(String(128), default="")
    cs_id: Mapped[str] = mapped_column(String(64), default="")
    channel: Mapped[str] = mapped_column(String(16), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    currency: Mapped[str] = mapped_column(String(8), default="", comment="收入币种（Shopify 订单币种）")
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None, comment="行项收入")
    product_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None, comment="渠道货品成本")
    shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None, comment="实际运费")
    best_shipping_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None, comment="三仓比价最优运费")
    platform_fee: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None, comment="平台抽成（交易费）")
    profit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None, comment="毛利 = 收入 - 全部成本")
    cost_currency: Mapped[str] = mapped_column(String(8), default="", comment="成本币种（渠道报价币种）")
    detail: Mapped[dict | None] = mapped_column(JSON, default=None, comment="核算明细（运费比价过程等）")
