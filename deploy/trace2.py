# -*- coding: utf-8 -*-
"""修正版: redirects 翻页全量 + soldout 按多仓求和判定。"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

reds, params = [], {"limit": 250}
while True:
    r = cl._client.get("redirects.json", params=params, auth=cl._auth)
    r.raise_for_status()
    reds += r.json()["redirects"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print(f"redirects 总数: {len(reds)}")
for x in reds:
    if "kitfort-kr-2505" in x["path"]:
        print(f"  {x['path'][-30:]} -> ...{x['target'][-50:]}")

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

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

n = tot = 0
for p in [x for x in allp if len(x.get("variants") or []) > 1]:
    iids = [str(v["inventory_item_id"]) for v in p["variants"]
            if v.get("inventory_item_id")]
    r = cl._client.get("inventory_levels.json",
                       params={"inventory_item_ids": ",".join(iids[:50])},
                       auth=cl._auth)
    agg = {}
    for x in r.json().get("inventory_levels", []):
        agg[x["inventory_item_id"]] = agg.get(x["inventory_item_id"], 0) \
            + x["available"]
    for v in p["variants"]:
        tot += 1
        if agg.get(v.get("inventory_item_id"), 0) <= 0:
            csid = (v.get("sku") or "").split("_")[0]
            cc.execute("SELECT COALESCE(SUM(quantity),0) FROM cs_inventory "
                       "WHERE cs_id=%s", (csid,))
            n += 1
            print(f"SOLD {p['handle'][:40]} {v['option1']:>9} "
                  f"{csid:<15} 源={cc.fetchone()[0]}")
print(f"多变体合计 {tot} 个变体, 真 soldout: {n}")
cs.close()
