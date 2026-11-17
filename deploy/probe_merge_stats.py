# -*- coding: utf-8 -*-
"""交叉统计：源库变体组 x 本地映射 x 线上 ACTIVE -> 可合并规模。"""
import os
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product")
groups = defaultdict(list)
for cs_id, pn, fm, cap in cc.fetchall():
    if pn and fm:  # 排除空键
        groups[(pn, fm)].append((cs_id, cap))
cs.close()

main = pymysql.connect(
    host=os.environ["SHOPIFY_DB_HOST"],
    port=int(os.environ.get("SHOPIFY_DB_PORT", 3306)),
    user=os.environ["SHOPIFY_DB_USER"],
    password=os.environ["SHOPIFY_DB_PASSWORD"],
    database=os.environ["SHOPIFY_DB_NAME"], charset="utf8mb4")
mc = main.cursor()

# sku -> (shopify_product_id, status, price)
mc.execute("""SELECT v.sku, v.shopify_product_id, p.status, v.price
              FROM product_variants v JOIN products p
                ON p.shopify_product_id = v.shopify_product_id
                  AND p.store_id = v.store_id
              WHERE v.sku IS NOT NULL AND v.sku != ''""")
sku_map = {}
for sku, pid, st, price in mc.fetchall():
    sku_map[sku] = (pid, st, price)
main.close()

mergeable = 0          # 组内线上 ACTIVE >= 2
online_products = 0    # 涉及线上 ACTIVE 产品数
pages_saved = 0
samples = []
for key, members in groups.items():
    caps = {c for _, c in members if c}
    if len(caps) < 2:
        continue
    live = [(cs_id, cap) + sku_map[cs_id]
            for cs_id, cap in members if cs_id in sku_map
            and sku_map[cs_id][1] == "active"]
    if len(live) >= 2 and len({v[1] for v in live}) >= 2:
        mergeable += 1
        online_products += len(live)
        pages_saved += len(live) - 1
        if len(samples) < 3:
            samples.append((key, live))

print(f"可合并组(线上>=2个ACTIVE且容量>=2种): {mergeable}")
print(f"涉及线上 ACTIVE 产品: {online_products}")
print(f"合并后可减少产品页: {pages_saved}")

for i, (key, live) in enumerate(samples):
    print(f"\n[样例{i+1}] part_no={str(key[0])[:35]!r}")
    for cs_id, cap, pid, st, price in live:
        mc2 = None
        print(f"  - {cs_id} cap={cap!r} price={price} pid={pid}")
