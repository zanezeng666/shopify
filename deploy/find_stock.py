# -*- coding: utf-8 -*-
"""探查 CS 侧库存数据源。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    tables = [r[0] for r in c.execute(text("SHOW TABLES")).all()]
    print("cs_new tables:", tables)
    # 找库存/stock/inventory 相关表
    for t in tables:
        cols = [r[0] for r in c.execute(text(f"SHOW COLUMNS FROM `{t}`")).all()]
        hit = [x for x in cols if any(k in x.lower() for k in ("stock", "qty", "quantity", "inventory"))]
        if hit:
            n = c.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar()
            print(f"\n{t} ({n} rows): 库存相关列 {hit}")
            print("  all cols:", cols)
