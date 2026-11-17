# -*- coding: utf-8 -*-
"""刷新 CS 库存快照（bmai CIM API -> cs_new.cs_inventory）+ 前后对照。"""
import sys

sys.path.insert(0, "/data/bmai/src")
from sqlalchemy import text  # noqa: E402
from bmai.core.database import cs_engine  # noqa: E402

eng = cs_engine.engine


def snap(tag):
    with eng.connect() as c:
        r = c.execute(text(
            "SELECT MAX(updated_at), COUNT(*), COUNT(DISTINCT cs_id), "
            "SUM(quantity>0) FROM cs_inventory")).one()
        in_stock = c.execute(text(
            "SELECT cs_id FROM cs_inventory GROUP BY cs_id "
            "HAVING SUM(quantity)>0")).fetchall()
        print(f"[{tag}] max_updated={r[0]} rows={r[1]} csids={r[2]} "
              f"pos_rows={r[3]} csids_in_stock={len(in_stock)}", flush=True)


snap("before")
from bmai.services.cs.sync import sync_inventory  # noqa: E402
errs = sync_inventory(["US", "HK", "SZ"], rcustomerno="2477")
print("sync errors:", errs)
snap("after")
