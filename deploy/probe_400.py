# -*- coding: utf-8 -*-
"""抓变体创建 400 的原始响应体。"""
import os
import sys

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

# 先看主品当前结构
mp = cl.request("GET", "products/15484830548212.json").get("product", {})
print("options:", mp["options"])
for v in mp["variants"]:
    print("variant:", v.get("option1"), v.get("price"), v.get("sku"))

r = cl._client.post("products/15484830548212/variants.json",
                    json={"variant": {"option1": "3000mAh", "price": "109.00",
                                      "grams": 0, "requires_shipping": True}},
                    auth=cl._auth)
print("\nPOST 状态:", r.status_code)
print(r.text[:500])
