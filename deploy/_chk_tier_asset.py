# -*- coding: utf-8 -*-
"""临时: 读回 main-product.liquid 确认 tier 注入."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
a = c.request("GET", "themes/190031036660/assets.json",
              params={"asset[key]": "sections/main-product.liquid"})["asset"]["value"]
print("tier-v1 in asset:", "estry-tier-v1" in a)
print("b2b-cta in asset:", "estry-b2b-cta" in a)
print("tier price rows:", a.count("etier__p"))
