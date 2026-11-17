# -*- coding: utf-8 -*-
"""聚焦：成本表覆盖度、货币、sku_csid 映射、listing_price 权威价。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== cs_product_price: price_type x location 分布 + 货币 ==")
    for r in c.execute(text(
            "SELECT location, price_type, currency, COUNT(*) n, "
            "MIN(current_price) pmin, MAX(current_price) pmax, "
            "ROUND(AVG(current_price),2) pavg, MAX(synced_at) last_sync "
            "FROM cs_new.cs_product_price GROUP BY location, price_type, currency")).all():
        print(f"   loc={r[0]:3} type={r[1]:10} cur={r[2]:4} n={r[3]:6} "
              f"价${r[4]}~${r[5]} 均${r[6]} 最近同步={r[7]}")

    print("\n== cs_product_price 样本（一个 cs_id 的全价格行） ==")
    for r in c.execute(text(
            "SELECT p.cs_id, p.location, p.price_type, p.current_price, p.currency "
            "FROM cs_new.cs_product_price p WHERE p.cs_id IN "
            " (SELECT cs_id FROM cs_new.cs_product_price LIMIT 3) "
            "ORDER BY p.cs_id, p.location, p.price_type")).all():
        print("   ", r)

    print("\n== 成本覆盖：cs_product vs cs_product_price ==")
    r = c.execute(text(
        "SELECT (SELECT COUNT(DISTINCT cs_id) FROM cs_new.cs_product), "
        "(SELECT COUNT(DISTINCT cs_id) FROM cs_new.cs_product_price), "
        "(SELECT COUNT(DISTINCT cs_id) FROM cs_new.cs_product_price "
        " WHERE location='US' AND price_type='dropship'), "
        "(SELECT COUNT(DISTINCT cs_id) FROM cs_new.cs_product_price "
        " WHERE location='HK' AND price_type='dropship')")).one()
    print(f"   cs_product={r[0]} 有价格={r[1]} US_dropship={r[2]} HK_dropship={r[3]}")

    print("\n== amazon.sku_csid ==")
    cl = [x[0] for x in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='sku_csid' "
        "ORDER BY ordinal_position")).all()]
    print("   列:", cl)
    for r in c.execute(text("SELECT * FROM amazon.sku_csid LIMIT 5")).all():
        print("   ", dict(zip(cl, r)))
    print("   行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.sku_csid")).scalar())

    print("\n== amazon.listing_price ==")
    cl2 = [x[0] for x in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='listing_price' "
        "ORDER BY ordinal_position")).all()]
    print("   列:", cl2)
    for r in c.execute(text("SELECT * FROM amazon.listing_price ORDER BY id DESC LIMIT 6")).all():
        print("   ", dict(zip(cl2, r)))
    print("   行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.listing_price")).scalar())

    print("\n== all_listings_report 新鲜度（最近 add_date 分组） ==")
    for r in c.execute(text(
            "SELECT add_date, COUNT(*) n FROM amazon.all_listings_report "
            "GROUP BY add_date ORDER BY add_date DESC LIMIT 8")).all():
        print(f"   {r[0]}  n={r[1]}")
    print("   Active 行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.all_listings_report WHERE status='Active'")).scalar(),
        " distinct sku:", c.execute(text(
            "SELECT COUNT(DISTINCT seller_sku) FROM amazon.all_listings_report "
            "WHERE status='Active'")).scalar())

    print("\n== amazon_new.sku_mapping / listing_group 概览 ==")
    for tbl in ("sku_mapping", "listing_group"):
        cl3 = [x[0] for x in c.execute(text(
            f"SELECT column_name FROM information_schema.columns "
            f"WHERE table_schema='amazon_new' AND table_name='{tbl}' "
            f"ORDER BY ordinal_position")).all()]
        print(f"   [{tbl}] 列:", cl3)
        for r in c.execute(text(
                f"SELECT * FROM amazon_new.{tbl} LIMIT 3")).all():
            print("     ", dict(zip(cl3, r)))
        print("     行数:", c.execute(text(
            f"SELECT COUNT(*) FROM amazon_new.{tbl}")).scalar())
