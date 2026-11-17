# -*- coding: utf-8 -*-
"""步骤2：20 样本全店铺价格明细落盘（JSON），含 SKU/ASIN 以便联标题判 Pack。"""
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
    # 1) amazon_inventory 完整字段
    cols = c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='amazon_inventory' "
        "ORDER BY ordinal_position")).all()
    out["inv_cols"] = [f"{n}:{t}" for n, t in cols]
    inv_col_names = [n for n, _ in cols]

    # 2) all_listings_report 完整字段 + 快照日期分布
    cols2 = c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='all_listings_report' "
        "ORDER BY ordinal_position")).all()
    out["alr_cols"] = [f"{n}:{t}" for n, t in cols2]
    alr_names = [n for n, _ in cols2]
    date_col = next((x for x in ("report_date", "add_date", "snapshot_date",
                                 "create_time", "created_at") if x in alr_names), None)
    if date_col:
        rows = c.execute(text(
            f"SELECT {date_col}, COUNT(*) FROM amazon.all_listings_report "
            f"GROUP BY {date_col} ORDER BY 1 DESC LIMIT 8")).all()
        out["alr_dates"] = [(str(r[0])[:10], r[1]) for r in rows]

    # 3) 20 样本 inventory 全行（挑有的字段）
    want = [x for x in ("cs_id", "store_name", "market_id", "price", "add_date",
                        "seller_sku", "sku", "asin", "asin1", "quantity",
                        "product_name", "title", "name") if x in inv_col_names]
    sel = ", ".join(want)
    conds = " OR ".join(
        f"cs_id LIKE '%{s[3:] if s.startswith('CS-') else s}%'" for s in SAMPLES)
    rows = c.execute(text(
        f"SELECT {sel} FROM amazon.amazon_inventory WHERE ({conds})")).all()
    inv = [dict(zip(want, [str(x)[:80] if x is not None else None for x in r]))
           for r in rows]
    out["inventory_rows"] = inv
    out["inventory_n"] = len(inv)

with open("/tmp/amz_probe2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("rows:", out["inventory_n"], "saved /tmp/amz_probe2.json")
print("inv_cols:", out["inv_cols"])
print("alr_dates:", out.get("alr_dates"))
