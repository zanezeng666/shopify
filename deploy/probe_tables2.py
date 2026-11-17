# -*- coding: utf-8 -*-
"""探针: 候选出货表结构+时间跨度+csid覆盖(只读)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import get_cs_engine  # noqa: E402

with get_cs_engine().connect() as c:
    for db, t in [("cs_new", "cs_orders"), ("cs_new", "order_records"),
                  ("cs_bm", "amazon_orders"), ("cs_bm", "amazon_mcf_orders")]:
        try:
            cols = [r[0] for r in
                    c.execute(text(f"SHOW COLUMNS FROM {db}.{t}")).fetchall()]
            print(f"\n== {db}.{t} 列: {cols}")
            tcol = next((x for x in cols if "date" in x.lower()
                         or x.lower() in ("created_at", "purchase_date",
                                          "order_date", "create_time")), None)
            cid = next((x for x in cols if "cs_id" in x.lower()), None)
            if tcol and cid:
                r = c.execute(text(
                    f"SELECT MIN({tcol}), MAX({tcol}) FROM {db}.{t}"
                )).fetchone()
                n90 = c.execute(text(f"""
                    SELECT COUNT(DISTINCT {cid}) FROM {db}.{t}
                    WHERE {tcol} >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                      AND {cid} IS NOT NULL AND {cid} <> ''
                """)).fetchone()[0]
                print(f"   {tcol}: {r[0]} ~ {r[1]} | 近90天distinct {cid}: {n90}")
        except Exception as e:
            print(f"{db}.{t}: {str(e)[:120]}")
