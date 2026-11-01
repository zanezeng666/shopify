# -*- coding: utf-8 -*-
"""Shopify 平台轻量 DTO（service 层入参/出参的结构化形态）。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class OrderSyncResult(BaseModel):
    """一次拉单的结果摘要。"""

    store_id: int
    fetched: int = 0
    created: int = 0
    updated: int = 0
    cursor: str | None = Field(default=None, description="新的 created_at_min 游标")


class ProductSyncResult(BaseModel):
    store_id: int
    fetched: int = 0
    created: int = 0
    updated: int = 0


class InventorySyncResult(BaseModel):
    store_id: int
    checked: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0


class FulfillmentSubmitResult(BaseModel):
    order_id: int
    channel: str
    channel_order_ref: str = ""
    status: str = "submitted"


class VerifyResult(BaseModel):
    store_id: int
    ok: bool
    shop_name: str = ""
    domain: str = ""
    message: str = ""
    checked_at: datetime | None = None


class ShippingQuote(BaseModel):
    """渠道运费报价（三仓比价数据结构，渠道层填充）。"""

    channel: str
    service_name: str = ""
    price: Decimal = Decimal("0")
    currency: str = ""
    eta_days: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
