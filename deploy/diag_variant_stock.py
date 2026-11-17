# -*- coding: utf-8 -*-
"""诊断试点 5 组变体：库存状态 + 容量顺序。"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

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
print(f"主品数: {len(mains)}")

locs = cl._client.get("locations.json", auth=cl._auth).json()["locations"]
print("locations:", [(l["id"], l["name"], l.get("active")) for l in locs])

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

for p in mains:
    print(f"\n== {p['handle'][:65]}")
    iids = []
    for v in sorted(p["variants"], key=lambda x: x["position"]):
        sku = v.get("sku") or ""
        csid = sku.split("_")[0] if sku else ""
        inv = None
        if csid:
            cc.execute(
                "SELECT location, quantity FROM cs_inventory WHERE cs_id=%s",
                (csid,))
            inv = cc.fetchall()
        print(f"  pos{v['position']} {str(v['option1']):>10} "
              f"sku={sku[:28]:<28} inv_mgmt={v.get('inventory_management')} "
              f"iid={v.get('inventory_item_id')} cs_inv={inv}")
        if v.get("inventory_item_id"):
            iids.append(str(v["inventory_item_id"]))
    if iids:
        r = cl._client.get("inventory_levels.json",
                           params={"inventory_item_ids": ",".join(iids)},
                           auth=cl._auth)
        lvls = r.json().get("inventory_levels", [])
        print("  levels:", [(x["location_id"], x["available"]) for x in lvls])
cs.close()
