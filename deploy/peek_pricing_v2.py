# -*- coding: utf-8 -*-
"""定价体系数据探查 v2：费率表/承运路线/全表清单/成本线索/亚马逊价格。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== 承运路线 cs_shipping_carrier ==")
    for r in c.execute(text(
            "SELECT carrier_code, carrier_name, origin, destination, is_active "
            "FROM cs_shipping_carrier ORDER BY id")).all():
        print("  ", r)

    print("\n== 费率表统计（carrier_code × zone） ==")
    for r in c.execute(text(
            "SELECT carrier_code, zone, COUNT(*) n, MIN(weight_g) wmin, MAX(weight_g) wmax, "
            "MIN(price) pmin, MAX(price) pmax FROM cs_shipping_rate "
            "GROUP BY carrier_code, zone ORDER BY carrier_code, zone")).all():
        print(f"   {r[0]:10} zone{r[1]} 档数={r[2]:3} 重量{r[3]}~{r[4]}g 价${r[5]}~${r[6]}")

    print("\n== usps 费率抽样（zone 4，前 12 档） ==")
    for r in c.execute(text(
            "SELECT weight_g, price FROM cs_shipping_rate "
            "WHERE carrier_code='usps' AND zone=4 ORDER BY weight_g LIMIT 12")).all():
        print(f"   {r[0]:6}g  ${r[1]}")
    print("== cs_usps 费率抽样（zone 4，前 12 档） ==")
    for r in c.execute(text(
            "SELECT weight_g, price FROM cs_shipping_rate "
            "WHERE carrier_code='cs_usps' AND zone=4 ORDER BY weight_g LIMIT 12")).all():
        print(f"   {r[0]:6}g  ${r[1]}")

    print("\n== cs_new 全表 ==")
    for r in c.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='cs_new' ORDER BY table_name")).all():
        print("  ", r[0])

print("\n== amazon_new / amazon 全表 ==")
with eng.connect() as c:
    for db in ("amazon_new", "amazon"):
        try:
            rows = c.execute(text(
                f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema='{db}' ORDER BY table_name")).all()
            print(f"  [{db}]")
            for r in rows:
                print("    ", r[0])
        except Exception as e:  # noqa: BLE001
            print(f"  [{db}] ERR {e}")
