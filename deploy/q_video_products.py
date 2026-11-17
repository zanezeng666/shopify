# -*- coding: utf-8 -*-
"""确认视频所用 4 个产品的标题/类型/状态。"""
from dotenv import load_dotenv
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

load_dotenv("/home/jason/shopify-admin/.env")
cl = ShopifyRest(StoreService().get_client(1)).client
IDS = (4626694602852, 7840406470900, 4636646932580, 4626420138084)
r = cl.request("GET", "products.json",
               params={"ids": ",".join(map(str, IDS)),
                       "fields": "id,title,product_type,status"})
for p in sorted(r.get("products", []), key=lambda x: x["id"]):
    print(f"{p['id']} | {p['status']:8} | {p['product_type'][:28]:28} | "
          f"{p['title'][:64]}")
