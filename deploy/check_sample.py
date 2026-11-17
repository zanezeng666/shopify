# -*- coding: utf-8 -*-
"""确认样例产品在线状态与 v2.1 描述。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
p = rest.product_by_handle("battery-for-delonghi-colombina-evo-xml510-as00000910")
if not p:
    print("产品不存在")
    sys.exit(0)
print("status:", p.get("status"))
print("id:", p["id"])
print("online_url:", (p.get("link") or {}).get("href"))
b = p.get("body_html") or ""
print("v2.1_18px:", "font-size:18px" in b, "| green:", "#00A651" in b)
