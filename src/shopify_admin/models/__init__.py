# -*- coding: utf-8 -*-
"""shopify_new 库 ORM 模型。导入本包即注册全部表到 Base.metadata。"""

from shopify_admin.models.base import Base

# 各业务域模型（全部显式导入，保证 Alembic autogenerate 元数据完整）
from shopify_admin.models.store import Store  # noqa: F401
from shopify_admin.models.product import (  # noqa: F401
    Product, ProductVariant, Collection, ProductCollection, Metafield,
)
from shopify_admin.models.order import Order, OrderItem  # noqa: F401
from shopify_admin.models.inventory import (  # noqa: F401
    InventoryLocation, InventoryLevel, InventorySyncLog, InventorySyncPolicy,
)
from shopify_admin.models.fulfillment import FulfillmentOrder  # noqa: F401
from shopify_admin.models.finance import Payout, Transaction, OrderCost  # noqa: F401
from shopify_admin.models.marketing import GoogleProductField, GmcFeed  # noqa: F401
from shopify_admin.models.task import TaskResult  # noqa: F401

__all__ = [
    "Base", "Store",
    "Product", "ProductVariant", "Collection", "ProductCollection", "Metafield",
    "Order", "OrderItem",
    "InventoryLocation", "InventoryLevel", "InventorySyncLog", "InventorySyncPolicy",
    "FulfillmentOrder",
    "Payout", "Transaction", "OrderCost",
    "GoogleProductField", "GmcFeed",
    "TaskResult",
]
