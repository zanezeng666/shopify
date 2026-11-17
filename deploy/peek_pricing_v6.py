# -*- coding: utf-8 -*-
"""探查 amazon_inventory（用户指定的价格源）+ 停售状态字段。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== amazon.amazon_inventory 列结构 ==")
    cl = [r[0] for r in c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema='amazon' AND table_name='amazon_inventory' "
        "ORDER BY ordinal_position")).all()]
    print("   ", cl)

    print("\n== amazon_inventory 行数 ==")
    print("   ", c.execute(text(
        "SELECT COUNT(*) FROM amazon.amazon_inventory")).scalar())

    print("\n== 样本 6 行 ==")
    for r in c.execute(text(
            "SELECT * FROM amazon.amazon_inventory LIMIT 6")).all():
        print("   ", dict(zip(cl, r)))

    print("\n== 停售状态：cs_product_record.status 分布 ==")
    for r in c.execute(text(
            "SELECT status, COUNT(*) n FROM cs_new.cs_product_record "
            "GROUP BY status ORDER BY n DESC")).all():
        print(f"   {r[0]!r:30} n={r[1]}")

    print("\n== cs_product 全列（找状态/上下架字段） ==")
    cl2 = [r[0] for r in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='cs_new' AND table_name='cs_product' "
        "ORDER BY ordinal_position")).all()]
    print("   ", cl2)
    for col in cl2:
        if any(k in col.lower() for k in ("status", "state", "sale", "active")):
            print(f"   分布 {col}:")
            for r in c.execute(text(
                    f"SELECT {col}, COUNT(*) FROM cs_new.cs_product "
                    f"GROUP BY {col}")).all():
                print("     ", r)

    print("\n== cs_inventory.location 分布（库存仓位） ==")
    for r in c.execute(text(
            "SELECT location, COUNT(*) n, SUM(quantity) qty FROM cs_new.cs_inventory "
            "GROUP BY location")).all():
        print(f"   {r[0]!r:10} 行数={r[1]} 总量={r[2]}")
