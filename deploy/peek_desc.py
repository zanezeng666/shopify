# -*- coding: utf-8 -*-
"""看现有产品描述结构(zebra主品)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,body_html", "status": "active"}
hit = None
while not hit:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    for x in r.json()["products"]:
        if x["handle"].startswith("battery-for-zebra-zr138"):
            hit = x
            break
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

if not hit:
    print("未找到")
else:
    b = hit["body_html"] or ""
    print("handle:", hit["handle"])
    print("描述长度:", len(b))
    print("---- 前 800 ----")
    print(b[:800])
