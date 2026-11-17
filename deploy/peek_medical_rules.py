# -*- coding: utf-8 -*-
"""Medical Battery collection 规则详情。"""
import sys
import json

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
r = cl.request("GET", "smart_collections.json", params={"limit": 250})
for s in r.get("smart_collections", []):
    if "medical" in s["title"].lower() or s["title"].lower().startswith(
            ("shaver", "toothbrush", "personal", "microscope", "electronic", "thermal")):
        print(json.dumps({"id": s["id"], "title": s["title"],
                          "handle": s["handle"],
                          "rules": s.get("rules"),
                          "disjunctive": s.get("disjunctive")}, ensure_ascii=False))
