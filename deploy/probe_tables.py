# -*- coding: utf-8 -*-
"""探针: cs_new / cs_bm 表清单 + 候选出货/订单表的时间跨度(只读)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import get_cs_engine  # noqa: E402

with get_cs_engine().connect() as c:
    dbs = ["cs_new", "cs_bm"]
    for db in dbs:
        try:
            ts = c.execute(text(f"SHOW TABLES FROM {db}")).fetchall()
            print(f"\n== {db} 表({len(ts)}) ==")
            for (t,) in ts:
                print(f"  {t}")
        except Exception as e:
            print(f"{db}: {str(e)[:100]}")
