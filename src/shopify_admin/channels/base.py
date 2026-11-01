# -*- coding: utf-8 -*-
"""履约渠道抽象契约。

同步风格（与 bmai / 服务层一致）。每个渠道实现五项能力：
查库存 / 运费比价 / 下单 / 查单 / 跟踪。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ChannelInventory:
    channel: str
    sku: str
    available: int = 0
    cs_id: str = ""
    price: Decimal | None = None
    currency: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Parcel:
    """包裹描述（运费计算入参）。"""

    weight_g: int = 0
    length_cm: float = 0.0
    width_cm: float = 0.0
    height_cm: float = 0.0
    declared_value: Decimal = Decimal("0")
    items: list[dict[str, Any]] = field(default_factory=list)  # [{"sku","qty","cs_id"}]


@dataclass
class ShippingQuote:
    channel: str
    service_name: str = ""
    price: Decimal = Decimal("0")
    currency: str = ""
    eta_days: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Address:
    name: str = ""
    phone: str = ""
    country_code: str = ""
    province: str = ""
    city: str = ""
    zip: str = ""
    address1: str = ""
    address2: str = ""


@dataclass
class FulfillmentLine:
    sku: str
    quantity: int
    cs_id: str = ""
    order_item_id: str = ""  # 平台行项 ID（CS 去重台账键）


@dataclass
class FulfillmentRequest:
    """渠道下单请求（平台无关）。"""

    order_ref: str  # 平台订单标识（如 Shopify 订单号）
    lines: list[FulfillmentLine]
    ship_to: Address
    parcel: Parcel | None = None
    remark: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelOrderRef:
    channel: str
    order_id: str  # 渠道侧订单号
    third_order_no: str = ""  # 平台侧单号（第三方单号，状态查询回退键）
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChannelOrderStatus:
    channel: str
    status: str  # pending/processing/shipped/completed/cancelled/failed
    tracking_number: str = ""
    tracking_company: str = ""
    tracking_url: str = ""
    error_message: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class FulfillmentChannel(ABC):
    """履约渠道抽象（CS / FastRite 各自实现）。"""

    name: str = ""

    @abstractmethod
    def get_inventory(self, sku: str) -> ChannelInventory:
        """查询单 SKU 渠道库存。"""

    @abstractmethod
    def calculate_shipping(self, parcel: Parcel, dest: Address) -> list[ShippingQuote]:
        """运费报价（可多服务档）。"""

    @abstractmethod
    def submit_order(self, request: FulfillmentRequest) -> ChannelOrderRef:
        """渠道下单。"""

    @abstractmethod
    def get_status(self, ref: ChannelOrderRef) -> ChannelOrderStatus:
        """查询渠道订单状态（含跟踪号）。"""

    def verify(self) -> bool:
        """渠道可用性检测。"""
        return True
