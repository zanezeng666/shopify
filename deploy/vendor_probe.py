# -*- coding: utf-8 -*-
"""查全店 vendor 分布。"""
import sys
import time
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "status": "active", "fields": "id,vendor"}
cnt = Counter()
while True:
    time.sleep(0.8)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    for p in r.json()["products"]:
        cnt[p.get("vendor") or "(空)"] += 1
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
for v, n in cnt.most_common(12):
    print(n, v)
