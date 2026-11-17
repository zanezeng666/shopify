# -*- coding: utf-8 -*-
"""补库存进度（DB 日志表计数）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope

with session_scope() as s:
    r = s.execute(text(
        "SELECT COUNT(*), SUM(success), SUM(success=0) FROM inventory_sync_logs "
        "WHERE store_id=1 AND synced_at > '2026-11-05 00:21:00'")).one()
print("backfill 进度 rows/success/fail:", r)
