# -*- coding: utf-8 -*-
"""输出试点 5 组主品完整 URL + 301 样例。"""
import sys

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

for pref in PREFIXES:
    for p in [x for x in allp if x["handle"].startswith(pref)]:
        caps = ",".join(v["option1"] for v in p["variants"])
        print(f"https://estrybattery.com/products/{p['handle']}  [{caps}]")
