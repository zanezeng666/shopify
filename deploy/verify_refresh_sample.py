# -*- coding: utf-8 -*-
"""抽验 refresh_all.done 中的产品四项改动。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
ids = [int(x) for x in open("/home/jason/shopify-admin/deploy/refresh_all.done").read().split()][:2]
for pid in ids:
    p = cl.request("GET", f"products/{pid}.json",
                   params={"fields": "options,images,title,body_html"}).get("product", {})
    mf = cl.request("GET", f"products/{pid}/metafields.json",
                    params={"namespace": "seo"}).get("metafields", [])
    print(json.dumps({
        "id": pid, "title": p.get("title", "")[:44],
        "options": [o["name"] for o in p.get("options", [])],
        "alt0": (p.get("images") or [{}])[0].get("alt", "")[:44],
        "navy_h3": "border-bottom:2px solid #1B2A41" in (p.get("body_html") or ""),
        "compat_merged": "Compatibility</h3>" in (p.get("body_html") or ""),
        "seo": (mf[0]["value"][:70] + "…") if mf else None,
    }, ensure_ascii=False))
