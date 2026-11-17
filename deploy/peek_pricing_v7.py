# -*- coding: utf-8 -*-
"""amazon_inventory 快照分布/离群形态/覆盖度 + 停售明细。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== amazon_inventory add_date 分布（最新 10 个） ==")
    for r in c.execute(text(
            "SELECT add_date, COUNT(*) n, COUNT(DISTINCT cs_id) ncs, "
            "COUNT(DISTINCT store_name) nstore FROM amazon.amazon_inventory "
            "GROUP BY add_date ORDER BY add_date DESC LIMIT 10")).all():
        print(f"   {r[0]}  行={r[1]:7} cs_id={r[2]:6} 店铺={r[3]}")

    print("\n== 多店同品价格形态（最新快照日内抽 8 个多店 cs_id） ==")
    for r in c.execute(text(
            "SELECT cs_id FROM amazon.amazon_inventory "
            "WHERE add_date=(SELECT MAX(add_date) FROM amazon.amazon_inventory) "
            "GROUP BY cs_id HAVING COUNT(DISTINCT store_name)>=3 LIMIT 8")).all():
        cs = r[0]
        prices = c.execute(text(
            "SELECT store_name, price, market_id FROM amazon.amazon_inventory "
            "WHERE cs_id=:c AND add_date=(SELECT MAX(add_date) "
            "FROM amazon.amazon_inventory WHERE cs_id=:c) ORDER BY CAST(price AS DECIMAL(10,2))"),
            {"c": cs}).all()
        print(f"   {cs}: " + " | ".join(f"{p[0]}=${p[1]}({p[2][:4]})" for p in prices))

    print("\n== 最新快照覆盖：amazon 价 vs cs_product ==")
    r = c.execute(text(
        "SELECT COUNT(DISTINCT ai.cs_id) FROM amazon.amazon_inventory ai "
        "WHERE ai.add_date=(SELECT MAX(add_date) FROM amazon.amazon_inventory) "
        "AND EXISTS (SELECT 1 FROM cs_new.cs_product p WHERE p.cs_id=ai.cs_id)")).scalar()
    print("   最新快照且在 cs_product 的 cs_id:", r)
    r2 = c.execute(text(
        "SELECT COUNT(DISTINCT cs_id) FROM amazon.amazon_inventory "
        "WHERE cs_id IN (SELECT cs_id FROM cs_new.cs_product)")).scalar()
    print("   全历史（含旧快照）在 cs_product 的 cs_id:", r2)

    print("\n== 每个快照日的独立覆盖（近5日） ==")
    for r in c.execute(text(
            "SELECT add_date, COUNT(DISTINCT cs_id) FROM amazon.amazon_inventory "
            "WHERE cs_id IN (SELECT cs_id FROM cs_new.cs_product) "
            "GROUP BY add_date ORDER BY add_date DESC LIMIT 5")).all():
        print(f"   {r[0]}  cs_id={r[1]}")

    print("\n== 停售明细：cs_product.status=0 ==")
    for r in c.execute(text(
            "SELECT cs_id, brand, status FROM cs_new.cs_product "
            "WHERE status=0 LIMIT 15")).all():
        print("   ", r)

    print("\n== cs_product_record Stop/Delete 类（最新记录为停售的 cs_id） ==")
    for r in c.execute(text(
            "SELECT cs_id, status, change_date FROM cs_new.cs_product_record "
            "WHERE status IN ('Stop Production','Delete','Stop Limit In Stock') "
            "ORDER BY change_date DESC LIMIT 15")).all():
        print("   ", r)

    print("\n== 交叉：record 停售 cs_id 是否已 status=0 ==")
    r = c.execute(text(
        "SELECT COUNT(DISTINCT r.cs_id) FROM cs_new.cs_product_record r "
        "WHERE r.status IN ('Stop Production','Delete','Stop Limit In Stock') "
        "AND EXISTS (SELECT 1 FROM cs_new.cs_product p WHERE p.cs_id=r.cs_id AND p.status=0)")).scalar()
    print("   record 停售且 status=0:", r)
