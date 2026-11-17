# -*- coding: utf-8 -*-
"""补救: 全部多变体品重 GET 拿 iid, 按 sku->cs_inventory SUM 直推。"""
import os
import sys
import time

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
cl = rest.client

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

locs = cl._client.get("locations.json", auth=cl._auth).json()["locations"]
LOC = next(l["id"] for l in locs if "Cameron" in l["name"])

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,variants", "status": "active"}
allp = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

multi = [p for p in allp if len(p.get("variants") or []) > 1]
print(f"多变体品: {len(multi)}")
fixed = skipped = 0
for p in multi:
    for v in p["variants"]:
        sku = v.get("sku") or ""
        csid = sku.split("_")[0] if sku else ""
        iid = v.get("inventory_item_id")
        if not (csid and iid):
            skipped += 1
            continue
        cc.execute("SELECT COALESCE(SUM(quantity),0) FROM cs_inventory "
                   "WHERE cs_id=%s", (csid,))
        q = int(cc.fetchone()[0])
        r = cl._client.get("inventory_levels.json",
                           params={"inventory_item_ids": iid}, auth=cl._auth)
        lv = {x["location_id"]: x["available"]
              for x in r.json().get("inventory_levels", [])}
        if lv.get(LOC) == q:
            continue
        rest.set_inventory_level(iid, LOC, q)
        fixed += 1
    time.sleep(0.2)
cs.close()
print(f"修正 {fixed} 个变体水位, 无 sku/iid 跳过 {skipped}")
