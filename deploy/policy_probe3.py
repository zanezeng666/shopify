# -*- coding: utf-8 -*-
"""footer.liquid 链接区结构 + REST/GraphQL 政策 url 桥接验证。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = "190031036660"
c = ShopifyRest(StoreService().get_client(1)).client

pols = c.request("GET", "policies.json").get("policies", [])
for p in pols:
    print("REST:", p["handle"], "→", p.get("url"))
g = c.graphql("{ shop { shopPolicies { id title url } } }")
for n in g["shop"]["shopPolicies"]:
    print("GQL:", n["id"].rsplit("/", 1)[-1], n["title"], "→", n["url"])

a = c.request("GET", f"themes/{TID}/assets.json",
              params={"asset[key]": "sections/footer.liquid"})
val = a.get("asset", {}).get("value", "")
print("footer 长度:", len(val))
for i, line in enumerate(val.splitlines()):
    if ("policies" in line or "/pages/" in line or "menu" in line.lower()
            or "linklists" in line):
        print(f"L{i}: {line.strip()[:150]}")
