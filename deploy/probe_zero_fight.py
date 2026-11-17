# -*- coding: utf-8 -*-
"""实锤: zebra 变体当前水位 + 本地镜像记录 + 谁在改。"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,variants", "status": "active"}
ps = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    ps += [x for x in r.json()["products"]
           if x["handle"].startswith("battery-for-zebra-zr138")]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt or ps:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
if not ps:
    print("翻页未取到")
else:
    p = ps[0]
    for v in p["variants"]:
        print(f"{v['option1']} sku={v.get('sku')} iid={v.get('inventory_item_id')}")
        rr = cl._client.get("inventory_levels.json", params={
            "inventory_item_ids": v.get("inventory_item_id")},
            auth=cl._auth)
        for x in rr.json().get("inventory_levels", []):
            print(f"   loc={x['location_id']} avail={x['available']} "
                  f"updated={x.get('updated_at')}")

# 本地镜像库
for tbl in ("shopify_variants", "variants", "inventory_mirror",
            "shop_inventory"):
    try:
        db = pymysql.connect(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("DB_PORT", 3306)),
            user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"], charset="utf8mb4")
        cc = db.cursor()
        cc.execute(f"SHOW TABLES LIKE '%{tbl}%'")
        if cc.fetchone():
            print("本地表命中:", tbl)
        db.close()
    except Exception as e:
        pass
