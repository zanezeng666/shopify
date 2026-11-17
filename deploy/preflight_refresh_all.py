# -*- coding: utf-8 -*-
"""全量刷前置摸底：窗口产品数 / 店名确认。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
shop = cl.request("GET", "shop.json")["shop"]
print("shop.name =", shop.get("name"))
cnt = cl.request("GET", "products/count.json",
                 params={"created_at_min": "2026-10-30T00:00:00Z"})
print("窗口内(>=2026-10-30) =", cnt.get("count"))
