# -*- coding: utf-8 -*-
"""迁移结果核验：新库计数 + 抽样。"""
import sys

sys.path.insert(0, "src")

from sqlalchemy import text

from shopify_admin.core.database import get_engine

with get_engine().connect() as c:
    for t in ["stores", "orders", "order_items", "products", "product_variants"]:
        n = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"{t}: {n}")
    print("--- 抽样:")
    for r in c.execute(text(
        "SELECT id, username, domain, rcustomerno, main_ship_by FROM stores"
    )):
        print("store:", tuple(r))
    for r in c.execute(text(
        "SELECT shopify_order_id, name, local_status, channel, created_at FROM orders "
        "ORDER BY id DESC LIMIT 3"
    )):
        print("order:", tuple(r))
    for r in c.execute(text(
        "SELECT oi.sku, oi.cs_id, oi.quantity, o.local_status FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id ORDER BY oi.id DESC LIMIT 3"
    )):
        print("item:", tuple(r))
