# -*- coding: utf-8 -*-
"""查最近库存同步日志。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope

with session_scope() as s:
    rows = s.execute(text(
        "SELECT sku, LEFT(message, 150), created_at "
        "FROM inventory_sync_logs ORDER BY id DESC LIMIT 6")).all()
for r in rows:
    print(r)
