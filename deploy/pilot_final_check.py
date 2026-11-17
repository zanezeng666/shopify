# -*- coding: utf-8 -*-
"""试点 5 组主品终检：变体完整性（price=0 / sku=None 标记）。"""
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

issues = 0
# 全量拉 active 自建品，按 handle 前缀过滤
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
    prods = [p for p in allp if p["handle"].startswith(pref)]
    for p in prods:
        print(f"\n== {p['handle'][:65]}")
        for v in p["variants"]:
            flag = ""
            if not v.get("sku"):
                flag += " <NO-SKU>"
            if float(v["price"] or 0) == 0:
                flag += " <ZERO-PRICE>"
            issues += bool(flag)
            print(f"   {v['option1']:<10} ${v['price']:<8} {v.get('sku')}{flag}")
print(f"\n异常数: {issues}")
