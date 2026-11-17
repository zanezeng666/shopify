# -*- coding: utf-8 -*-
"""全量 collections title/handle 映射（设计导航用）。"""
import sys
import json

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client


def paged(path):
    items, params = [], {"limit": 250}
    while True:
        r = cl._client.get(path, params=params, auth=cl._auth)
        r.raise_for_status()
        items += r.json()[path.split(".")[0]]
        link = r.headers.get("Link", "")
        nxt = [p.split(";")[0].strip("<>") for p in link.split(",")
               if 'rel="next"' in p]
        if not nxt:
            return items
        params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}


out = {}
for path in ("smart_collections.json", "custom_collections.json"):
    for c in paged(path):
        out[c["title"]] = {"handle": c["handle"], "id": c["id"]}
print(json.dumps(out, ensure_ascii=False, indent=0))
print("共", len(out))
