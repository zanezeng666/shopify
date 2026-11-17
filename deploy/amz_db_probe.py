# -*- coding: utf-8 -*-
"""比价口径切换：直查 amazon 库（自家平台所有店/卖家价），不爬前台。
步骤1：探表结构 + 20 样本全店铺价格明细。"""
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
with eng.connect() as c:
    print("== amazon 库表清单 ==")
    tabs = c.execute(text(
        "SELECT table_name, table_rows FROM information_schema.tables "
        "WHERE table_schema='amazon' ORDER BY table_name")).all()
    for t, n in tabs:
        print(f"   {t}  ~{n} rows")

    print("\n== amazon_inventory 字段 ==")
    cols = c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='amazon_inventory' "
        "ORDER BY ordinal_position")).all()
    print("   " + ", ".join(f"{n}:{t}" for n, t in cols))

    print("\n== all_listings_report 字段 ==")
    cols = c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='all_listings_report' "
        "ORDER BY ordinal_position")).all()
    print("   " + ", ".join(f"{n}:{t}" for n, t in cols))

    print("\n== 20 样本 amazon_inventory 全明细 ==")
    # cs_id 形态不确定（带/不带 CS- 前缀），用核心段匹配
    conds = " OR ".join(
        f"cs_id LIKE '%{s[3:] if s.startswith('CS-') else s}%'" for s in SAMPLES)
    rows = c.execute(text(
        f"SELECT cs_id, store_name, market_id, price, add_date "
        f"FROM amazon.amazon_inventory WHERE ({conds}) "
        f"ORDER BY cs_id, add_date")).all()
    cur = None
    for cs_id, store, mkt, price, d in rows:
        if cs_id != cur:
            cur = cs_id
            print(f"\n   [{cs_id}]")
        print(f"     {str(d)[:10]} | {store} | {mkt} | {price}")
    if not rows:
        print("   (无匹配行，需检查 cs_id 形态)")

    print("\n== store_name 全店铺分布（inventory 有价的） ==")
    rows = c.execute(text(
        "SELECT store_name, COUNT(*) FROM amazon.amazon_inventory "
        "WHERE price IS NOT NULL AND CAST(price AS DECIMAL(10,2))>0 "
        "GROUP BY store_name ORDER BY 2 DESC")).all()
    for s, n in rows:
        print(f"   {s}: {n}")
