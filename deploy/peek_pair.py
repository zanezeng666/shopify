# -*- coding: utf-8 -*-
"""取一个未刷新的对照产品 handle。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope

with session_scope() as s:
    rows = s.execute(text(
        "SELECT p.handle FROM products p "
        "WHERE p.store_id=1 AND p.status='active' "
        "AND p.created_at >= '2026-11-04 19:50:00' "
        "AND p.id != 22008 ORDER BY p.id LIMIT 1")).all()
for r in rows:
    print("https://estrybattery.com/products/" + r[0])
