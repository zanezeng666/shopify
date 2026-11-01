# -*- coding: utf-8 -*-
"""履约渠道抽象层：CS 供应商（复用 bmai）/ FastRite 海外仓（自建）。

业务服务只依赖 FulfillmentChannel 抽象，渠道可替换、可扩展。
"""
from shopify_admin.channels.base import (
    ChannelInventory, ChannelOrderRef, ChannelOrderStatus, FulfillmentRequest,
    FulfillmentChannel, Parcel, ShippingQuote,
)

__all__ = [
    "FulfillmentChannel", "ChannelInventory", "ChannelOrderRef", "ChannelOrderStatus",
    "FulfillmentRequest", "Parcel", "ShippingQuote",
]
