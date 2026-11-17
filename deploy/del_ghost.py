# -*- coding: utf-8 -*-
"""删除 dewalt 主品上的幽灵 3000mAh 变体（组内无此容量）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
p = cl.request("GET", "products/15484830548212.json",
               params={"fields": "variants"}).get("product", {})
for v in p["variants"]:
    if v["option1"] == "3000mAh":
        cl.request("DELETE", f"variants/{v['id']}.json")
        print(f"deleted ghost variant {v['id']} 3000mAh")
print("剩余:", [(v["option1"], v["price"], v["sku"]) for v in
      cl.request("GET", "products/15484830548212.json",
                 params={"fields": "variants"})["product"]["variants"]])
