# -*- coding: utf-8 -*-
"""查 150 个无源映射 sku 的形态。"""
import os
import sys
from collections import Counter

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id FROM cs_product")
csids = {r[0] for r in cc.fetchall()}
cs.close()

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,status,variants", "status": "active"}
orphans = Counter()
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    for p in r.json()["products"]:
        sku = (p["variants"] or [{}])[0].get("sku") or ""
        cs_id = sku.split("_")[0] if sku else ""
        if cs_id not in csids:
            orphans[cs_id] += 1
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
           if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

print("无映射 sku 前缀计数:", dict(orphans.most_common(10)))
print("总计:", sum(orphans.values()))
