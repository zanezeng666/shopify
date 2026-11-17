# -*- coding: utf-8 -*-
"""最终抽验：新品库存水位。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
q = """
{
  productByHandle(handle: "%s") {
    status
    variants(first: 1) { nodes { sku price inventoryQuantity } }
  }
}"""
for h in ("battery-for-delonghi-colombina-evo-xml510-as00000910",
          "battery-for-concept-vr3120-vr3125-vr3205-vr3210-vr3215-vr3400-vr350",
          "battery-for-sencor-srv-2010ti-srv-2010ti-cleentino-srx-0026-srx-0"):
    r = c.graphql(q % h)
    p = r["productByHandle"] or {}
    v = (p.get("variants", {}).get("nodes") or [{}])[0]
    print(f"{h[:46]:46} {p.get('status')} {v.get('sku')} ${v.get('price')} qty={v.get('inventoryQuantity')}")
