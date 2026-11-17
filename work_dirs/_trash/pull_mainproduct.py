# -*- coding: utf-8 -*-
"""拉 main-product.liquid + 找 buy-buttons/quantity 位置。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
a = rest.request("GET", f"themes/{TID}/assets.json",
                 params={"asset[key]": "sections/main-product.liquid"})["asset"]
v = a["value"]
open("/tmp/main_product.liquid", "w", encoding="utf-8").write(v)
print("bytes:", len(v))
for pat in [r"buy-buttons", r"product-form", r"quantity-input", r"price__", r"share-button", r"@media"]:
    hits = [v[:m.start()].count("\n") + 1 for m in re.finditer(pat, v)][:6]
    print(pat, "lines:", hits)
