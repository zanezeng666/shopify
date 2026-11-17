# -*- coding: utf-8 -*-
"""探查成本表/亚马逊价格表的列结构、主键、覆盖量与匹配链路。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()


def cols(c, db, tbl):
    rows = c.execute(text(
        f"SELECT column_name, column_type FROM information_schema.columns "
        f"WHERE table_schema='{db}' AND table_name='{tbl}' "
        f"ORDER BY ordinal_position")).all()
    print(f"  [{db}.{tbl}]")
    for n, t in rows:
        print(f"    {n:32} {t}")
    return [r[0] for r in rows]


with eng.connect() as c:
    print("== 列结构 ==")
    for tbl in ("cs_product_price", "cs_product_record", "cs_transaction_record"):
        cols(c, "cs_new", tbl)
    for tbl in ("sku_csid", "listing_price", "all_listings_report",
                "fba_product_cost_price", "special_price"):
        cols(c, "amazon", tbl)
    for tbl in ("sku_mapping", "listing_group", "listing_draft"):
        cols(c, "amazon_new", tbl)

    print("\n== cs_product_price 样本（5 行） ==")
    cl = c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='cs_new' AND table_name='cs_product_price' "
        "ORDER BY ordinal_position")).all()
    names = [r[0] for r in cl]
    for r in c.execute(text("SELECT * FROM cs_new.cs_product_price LIMIT 5")).all():
        print("   ", dict(zip(names, r)))
    print("  行数:", c.execute(text(
        "SELECT COUNT(*) FROM cs_new.cs_product_price")).scalar())

    print("\n== amazon.sku_csid 样本/行数 ==")
    for r in c.execute(text("SELECT * FROM amazon.sku_csid LIMIT 5")).all():
        print("   ", r)
    print("  行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.sku_csid")).scalar())

    print("\n== amazon.listing_price 样本/行数 ==")
    cl2 = [r[0] for r in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='listing_price' "
        "ORDER BY ordinal_position")).all()]
    for r in c.execute(text("SELECT * FROM amazon.listing_price LIMIT 5")).all():
        print("   ", dict(zip(cl2, r)))
    print("  行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.listing_price")).scalar())

    print("\n== amazon.all_listings_report 样本（找价格列） ==")
    cl3 = [r[0] for r in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='all_listings_report' "
        "ORDER BY ordinal_position")).all()]
    print("   列:", cl3)
    for r in c.execute(text("SELECT * FROM amazon.all_listings_report LIMIT 3")).all():
        print("   ", dict(zip(cl3, r)))
    print("  行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.all_listings_report")).scalar())
