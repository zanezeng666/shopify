# -*- coding: utf-8 -*-
"""交叉：源库变体组 x estrybattery 线上产品（REST 直拉）。"""
import os
import sys
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

# 1) 源库分组
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product")
groups = defaultdict(list)
for cs_id, pn, fm, cap in cc.fetchall():
    if pn and fm:
        groups[(pn, fm)].append((cs_id, cap))
cs.close()
csid2group = {}
for gi, (key, members) in enumerate(groups.items()):
    for cs_id, cap in members:
        csid2group[cs_id] = (gi, key, cap)

# 2) 线上产品直拉（自建 4510）
cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,title,status,variants"}
live = []
path = "products.json"
while True:
    r = cl._client.get(path, params=params, auth=cl._auth)
    r.raise_for_status()
    live += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
           if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print(f"线上自建产品: {len(live)} | active: "
      f"{sum(1 for p in live if p['status']=='active')}")

# 3) 交叉
by_group = defaultdict(list)   # gi -> [(cs_id,cap,pid,title,price)]
orphan = 0
for p in live:
    if p["status"] != "active":
        continue
    sku = (p["variants"] or [{}])[0].get("sku") or ""
    cs_id = sku.split("_")[0] if sku else ""
    if cs_id not in csid2group:
        orphan += 1
        continue
    gi, key, cap = csid2group[cs_id]
    price = (p["variants"] or [{}])[0].get("price")
    by_group[gi].append((cs_id, cap, p["id"], p["title"], price))

mergeable = 0
online_products = 0
pages_saved = 0
samples = []
for gi, members in by_group.items():
    if len(members) >= 2 and len({m[1] for m in members if m[1]}) >= 2:
        mergeable += 1
        online_products += len(members)
        pages_saved += len(members) - 1
        if len(samples) < 3:
            samples.append(members)

print(f"sku 无源映射: {orphan}")
print(f"== 可合并组: {mergeable} | 涉及线上产品 {online_products} "
      f"| 减少产品页 {pages_saved}")
for i, members in enumerate(samples):
    print(f"\n[样例{i+1}]")
    for cs_id, cap, pid, title, price in sorted(members, key=lambda x: x[1] or ""):
        print(f"  {cs_id:<16} cap={cap!r:<12} ${price}  {title[:55]}")
