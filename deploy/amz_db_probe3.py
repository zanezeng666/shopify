# -*- coding: utf-8 -*-
"""步骤3：20 样本在 all_listings_report 2026-11-06 快照的标题/价格（判 Pack 用）。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

SAMPLES = [
    "CS-HIQ200SL", "CS-TOX500TW", "CS-DEL552NB", "CS-SMR365SH", "CS-ABL100VX",
    "CS-MVS500VX", "CS-CHM170PR", "CS-FNT250TW", "CS-TMG610SL", "CS-ABM600SL",
    "CS-SFM3SL", "CS-DEW528PX", "CS-EMC150LS", "CS-KOH300MD", "CS-FVA034MD",
    "CS-ECR131VX", "CS-P303CL", "CS-RMA150MD", "CS-WGF300VX", "CS-BS3300PX",
]

eng = get_cs_engine()
out = {}
with eng.connect() as c:
    conds = " OR ".join(f"cs_id='{s}'" for s in SAMPLES)
    rows = c.execute(text(
        "SELECT cs_id, store_name, market_id, seller_sku, asin1, item_name, "
        "price, quantity, fulfillment_channel "
        "FROM amazon.all_listings_report "
        f"WHERE add_date='2026-11-06' AND ({conds})")).all()
    alr = []
    for cs_id, store, mkt, sku, asin, name, price, qty, fc in rows:
        alr.append({
            "cs_id": cs_id, "store": store, "mkt": mkt, "sku": sku,
            "asin": asin, "name": (name or "")[:200],
            "price": price, "qty": qty, "fc": fc,
        })
    out["alr_rows"] = alr
    out["alr_n"] = len(alr)

with open("/tmp/amz_probe3.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("alr rows:", out["alr_n"], "saved /tmp/amz_probe3.json")
from collections import Counter
print(Counter(r["cs_id"] for r in alr))
print(Counter(r["mkt"] for r in alr))
