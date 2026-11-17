# -*- coding: utf-8 -*-
"""收尾探查：listing_price 覆盖、all_listings 新鲜度、amazon_new 映射。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== amazon.listing_price 行数/样本 ==")
    print("   行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.listing_price")).scalar(),
        " distinct csid:", c.execute(text(
            "SELECT COUNT(DISTINCT csid) FROM amazon.listing_price")).scalar())
    for r in c.execute(text(
            "SELECT * FROM amazon.listing_price LIMIT 8")).all():
        print("   ", r)

    print("\n== all_listings_report add_date 分布（最近8个） ==")
    for r in c.execute(text(
            "SELECT add_date, COUNT(*) n FROM amazon.all_listings_report "
            "GROUP BY add_date ORDER BY add_date DESC LIMIT 8")).all():
        print(f"   {r[0]}  n={r[1]}")

    print("\n== all_listings Active：sku 可映射 cs_id 的量（前缀正则） ==")
    r = c.execute(text(
        "SELECT COUNT(*), COUNT(DISTINCT seller_sku) FROM amazon.all_listings_report "
        "WHERE status='Active' AND seller_sku REGEXP '^CS-[A-Z0-9]+'")).one()
    print("   Active&CS前缀:", r)

    print("\n== amazon_new.sku_mapping 列+样本 ==")
    cl = [x[0] for x in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon_new' AND table_name='sku_mapping' "
        "ORDER BY ordinal_position")).all()]
    print("   列:", cl)
    for r in c.execute(text(
            "SELECT * FROM amazon_new.sku_mapping LIMIT 4")).all():
        print("   ", dict(zip(cl, r)))
    print("   行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon_new.sku_mapping")).scalar())

    print("\n== amazon_new.listing_group 列+样本 ==")
    cl2 = [x[0] for x in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon_new' AND table_name='listing_group' "
        "ORDER BY ordinal_position")).all()]
    print("   列:", cl2)
    for r in c.execute(text(
            "SELECT * FROM amazon_new.listing_group LIMIT 4")).all():
        print("   ", dict(zip(cl2, r)))
    print("   行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon_new.listing_group")).scalar())

    print("\n== amazon.special_price 列+行数 ==")
    cl3 = [x[0] for x in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='special_price' "
        "ORDER BY ordinal_position")).all()]
    print("   列:", cl3)
    print("   行数:", c.execute(text(
        "SELECT COUNT(*) FROM amazon.special_price")).scalar())
    for r in c.execute(text(
            "SELECT * FROM amazon.special_price LIMIT 4")).all():
        print("   ", dict(zip(cl3, r)))
