# -*- coding: utf-8 -*-
"""老库表结构探查（迁移脚本前置调研）。"""
import sys

sys.path.insert(0, "src")

from sqlalchemy import text

from shopify_admin.core.database import get_legacy_engine

eng = get_legacy_engine()
with eng.connect() as c:
    tabs = [r[0] for r in c.execute(text("SHOW TABLES"))]
    print("tables:", tabs)
    for t in ["shopify_store_info", "orders_report", "shopify_product", "product_variant"]:
        if t in tabs:
            cols = c.execute(text(f"SHOW COLUMNS FROM {t}"))
            print(f"--- {t}: {[r[0] for r in cols]}")
            cnt = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"    rows={cnt}")
    # GMC 相关表
    for t in tabs:
        if "gmc" in t.lower() or "google" in t.lower():
            cols = c.execute(text(f"SHOW COLUMNS FROM {t}"))
            print(f"--- {t}: {[r[0] for r in cols]}")
            print(f"    rows={c.execute(text(f'SELECT COUNT(*) FROM {t}')).scalar()}")
