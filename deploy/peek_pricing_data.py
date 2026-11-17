# -*- coding: utf-8 -*-
"""定价体系数据探查：成本列/库存仓位/亚马逊价格表/费率表形态。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== cs_product 全部列 ==")
    rows = c.execute(text(
        "SELECT column_name, column_type FROM information_schema.columns "
        "WHERE table_schema='cs_new' AND table_name='cs_product' "
        "ORDER BY ordinal_position")).all()
    for n, t in rows:
        print(f"  {n:28} {t}")

    print("\n== cs_inventory 仓位分布 ==")
    rows = c.execute(text(
        "SELECT location, COUNT(*) cnt, SUM(quantity) qty FROM cs_inventory "
        "GROUP BY location ORDER BY qty DESC")).all()
    for loc, cnt, qty in rows:
        print(f"  {str(loc):20} 行数={cnt:6} 总量={qty}")

    print("\n== 费率表形态（每 carrier 抽样） ==")
    rows = c.execute(text(
        "SELECT carrier, COUNT(*) n, MIN(weight_g) wmin, MAX(weight_g) wmax, "
        "MIN(price) pmin, MAX(price) pmax, COUNT(DISTINCT zone) nz "
        "FROM cs_shipping_rate GROUP BY carrier")).all()
    for r in rows:
        print(f"  {str(r[0]):10} 行={r[1]:4} 重量{r[2]}-{r[3]}g "
              f"价{r[4]}-{r[5]} zone数={r[6]}")
    rows = c.execute(text(
        "SELECT carrier, weight_g, zone, price FROM cs_shipping_rate "
        "WHERE weight_g <= 500 ORDER BY carrier, weight_g LIMIT 24")).all()
    for r in rows:
        print(f"    {r[0]:10} {r[1]:5}g zone{r[2]} ${r[3]}")

    print("\n== cs_new 其它表（找价格/成本相关） ==")
    rows = c.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='cs_new' ORDER BY table_name")).all()
    print("  " + ", ".join(r[0] for r in rows))

print("\n== amazon_new / amazon 库的表 ==")
with eng.connect() as c:
    for db in ("amazon_new", "amazon"):
        try:
            rows = c.execute(text(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema='{db}' ORDER BY table_name")).all()
            print(f"  [{db}] " + ", ".join(r[0] for r in rows))
        except Exception as e:  # noqa: BLE001
            print(f"  [{db}] ERR {e}")
