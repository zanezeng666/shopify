# -*- coding: utf-8 -*-
"""看本轮真新品的 product 行回写情况。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope

with session_scope() as s:
    rows = s.execute(text(
        "SELECT p.id, p.handle, p.status, p.shopify_created_at, p.created_at "
        "FROM products p JOIN product_variants pv ON pv.product_id = p.id "
        "WHERE pv.store_id=1 AND pv.sku='CS-CNR300VX_DeLonghi_77_0'")).all()
    for r in rows:
        print(r)
    # 今日新建总数（本地行 created_at）
    n = s.execute(text(
        "SELECT COUNT(*) FROM products WHERE store_id=1 "
        "AND created_at >= '2026-11-04 19:50:00'")).scalar()
    print("本地行 created_at>=19:50:", n)
    n2 = s.execute(text(
        "SELECT COUNT(*) FROM products WHERE store_id=1 "
        "AND shopify_created_at IS NULL")).scalar()
    print("shopify_created_at 为 NULL:", n2)
