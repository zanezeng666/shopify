# -*- coding: utf-8 -*-
"""诊断 products/variants join 与新品回写字段。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope

with session_scope() as s:
    # DeLonghi 新品（已知 19:54 建）
    row = s.execute(text(
        "SELECT id, shopify_product_id, handle, status, shopify_created_at, shopify_updated_at "
        "FROM products WHERE store_id=1 AND handle LIKE 'battery-for-delonghi-colombina%' LIMIT 1")).one_or_none()
    print("product:", row)
    if row:
        v = s.execute(text(
            "SELECT id, product_id, sku, inventory_item_id FROM product_variants "
            "WHERE store_id=1 AND product_id=:pid"), {"pid": row[0]}).all()
        print("variants:", v)
    # 本轮新建产品的 created_at 分布
    n = s.execute(text(
        "SELECT COUNT(*) FROM products WHERE store_id=1 "
        "AND shopify_created_at >= '2026-11-04 19:50:00'")).scalar()
    print("created_at>=19:50 的产品数:", n)
    # products.status 分布
    for r in s.execute(text(
            "SELECT status, COUNT(*) FROM products WHERE store_id=1 GROUP BY status")).all():
        print("status:", r)
