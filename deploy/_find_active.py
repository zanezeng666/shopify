# -*- coding: utf-8 -*-
"""从 Shopify 远端实时拉 ACTIVE 产品 (带 CS- 变体 SKU)."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
r = c.request("GET", "products.json",
              params={"status": "active", "limit": 20, "fields": "handle,variants"})
n = 0
for p in r["products"]:
    for v in p.get("variants", []):
        sku = v.get("sku") or ""
        if sku.startswith("CS-"):
            print(p["handle"], "|", sku)
            n += 1
            break
    if n >= 4:
        break
