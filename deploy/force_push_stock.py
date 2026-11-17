# -*- coding: utf-8 -*-
"""绕过镜像判定，直接把 cs_inventory 库存推到线上 levels（前→推→后复验）。"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
cl = rest.client
LOC = 10117218404  # Cameron Sino 主仓（现有 levels 全在此）

PREFIXES = [
    "battery-for-al-ko-comfort-gt-1825",
    "battery-for-sichler-reinigungs-roboter",
    "battery-for-asus-eee-pc-703",
    "battery-for-dewalt-20v-max-60v-max-120v",
    "battery-for-dolmar-ah-3756",
]

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,variants", "status": "active"}
allp = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
           if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

mains = [p for pref in PREFIXES for p in allp if p["handle"].startswith(pref)]

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

fixed = 0
for p in sorted(mains, key=lambda x: x["handle"]):
    print(f"== {p['handle'][:55]}")
    for v in sorted(p["variants"], key=lambda x: x.get("position", 99)):
        sku = v.get("sku") or ""
        csid = sku.split("_")[0] if sku else ""
        iid = v.get("inventory_item_id")
        if not (csid and iid):
            print(f"  ! {v['option1']} 无 sku/iid 跳过")
            continue
        cc.execute("SELECT COALESCE(SUM(quantity),0) FROM cs_inventory "
                   "WHERE cs_id=%s", (csid,))
        target = int(cc.fetchone()[0])
        r = cl._client.get("inventory_levels.json",
                           params={"inventory_item_ids": iid}, auth=cl._auth)
        lv = {x["location_id"]: x["available"] for x in
              r.json().get("inventory_levels", [])}
        cur = lv.get(LOC)
        if cur == target:
            print(f"  ok {v['option1']:>9} 线上={cur} 目标={target}")
            continue
        rest.set_inventory_level(iid, LOC, target)
        r2 = cl._client.get("inventory_levels.json",
                            params={"inventory_item_ids": iid}, auth=cl._auth)
        lv2 = {x["location_id"]: x["available"] for x in
               r2.json().get("inventory_levels", [])}
        print(f"  fix {v['option1']:>9} {cur} -> {lv2.get(LOC)} "
              f"(目标={target})")
        fixed += 1
cs.close()
print(f"\n共修正 {fixed} 个变体库存")
