# -*- coding: utf-8 -*-
"""跨库差集核验：老库每个业务键是否都已落入新库（幂等性证明）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_engine

CHECKS = [
    ("products 遗漏", """
        SELECT COUNT(*) FROM shopify.shopify_product sp
        WHERE NOT EXISTS (SELECT 1 FROM shopify_new.products p
                          WHERE p.shopify_product_id = CAST(sp.id AS UNSIGNED))"""),
    ("variants 遗漏", """
        SELECT COUNT(*) FROM shopify.product_variant pv
        JOIN shopify.shopify_product sp ON sp.id = pv.product_id
        WHERE NOT EXISTS (SELECT 1 FROM shopify_new.product_variants v
                          WHERE v.shopify_variant_id = CAST(pv.id AS UNSIGNED))"""),
    ("orders 遗漏", """
        SELECT COUNT(*) FROM (SELECT DISTINCT order_id FROM shopify.orders_report) t
        WHERE NOT EXISTS (SELECT 1 FROM shopify_new.orders o
                          WHERE o.shopify_order_id = CAST(t.order_id AS UNSIGNED))"""),
    ("variants 多余（新库有老库无）", """
        SELECT COUNT(*) FROM shopify_new.product_variants v
        WHERE NOT EXISTS (SELECT 1 FROM shopify.product_variant pv
                          WHERE CAST(pv.id AS UNSIGNED) = v.shopify_variant_id)"""),
]

with get_engine().connect() as c:
    for label, sql in CHECKS:
        n = c.execute(text(sql)).scalar()
        print(f"{label}: {n}")
