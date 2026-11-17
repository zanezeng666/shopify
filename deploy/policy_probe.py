# -*- coding: utf-8 -*-
"""探 policies.json 结构与现有政策内容。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
pols = c.request("GET", "policies.json").get("policies", [])
p0 = pols[0] if pols else {}
print("keys:", sorted(p0.keys()))
for p in pols:
    if p.get("handle") in ("shipping-policy", "refund-policy"):
        b = p.get("body") or ""
        print(f"\n=== {p['handle']} ({len(b)} chars) ===")
        print(b[:600].replace("\n", " ")[:600])
# GraphQL 探 id
q = """
{ shop { shippingPolicy { id title } refundPolicy { id title }
  termsOfService { id } } }"""
try:
    g = c.graphql(q)
    print("\nGraphQL:", g)
except Exception as e:  # noqa: BLE001
    print("GraphQL FAIL:", str(e)[:200])
