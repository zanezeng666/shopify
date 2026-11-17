# -*- coding: utf-8 -*-
"""修最后 2 个 soldout: connect location + set 库存; 然后重跑 feed 扫描(带节流)。"""
import os
import sys
import time

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

locs = cl._client.get("locations.json", auth=cl._auth).json()["locations"]
LOC = next(l["id"] for l in locs if "Cameron" in l["name"])
FIX = [("battery-for-worx-landroid-s300", "CS-WRS300PW"),
       ("battery-for-zondan-apollo-n3", "CS-ZAN300MX")]
for hprefix, csid in FIX:
    params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
              "fields": "id,handle,variants", "status": "active"}
    hit = None
    while not hit:
        r = cl._client.get("products.json", params=params, auth=cl._auth)
        r.raise_for_status()
        for x in r.json()["products"]:
            if x["handle"].startswith(hprefix):
                hit = x
                break
        link = r.headers.get("Link", "")
        nxt = [y.split(";")[0].strip("<>")
               for y in link.split(",") if 'rel="next"' in y]
        if not nxt:
            break
        params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
    if not hit:
        print("未找到", hprefix)
        continue
    for v in hit["variants"]:
        if (v.get("sku") or "").startswith(csid):
            iid = v["inventory_item_id"]
            cc.execute("SELECT COALESCE(SUM(quantity),0) FROM cs_inventory "
                       "WHERE cs_id=%s", (csid,))
            q = int(cc.fetchone()[0])
            r = cl._client.post("inventory_levels/connect.json", auth=cl._auth,
                                json={"inventory_item_id": iid,
                                      "location_id": LOC})
            print(hprefix[:30], "connect:", r.status_code)
            r = cl._client.post(
                "inventory_levels/set.json", auth=cl._auth,
                json={"inventory_item_id": iid, "location_id": LOC,
                      "available": q})
            rr = cl._client.get("inventory_levels.json",
                                params={"inventory_item_ids": iid},
                                auth=cl._auth)
            tot = sum(x["available"]
                      for x in rr.json().get("inventory_levels", []))
            print(hprefix[:30], v["option1"], "源", q, "线上", tot)
cs.close()
