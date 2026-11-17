# -*- coding: utf-8 -*-
"""探针3: DiscountShippingDestinationSelection union 分支."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

r = c.graphql(
    "query T($n: String!) { __type(name: $n) { name kind possibleTypes { name } } }",
    {"n": "DiscountShippingDestinationSelection"},
)
ty = r.get("__type") or {}
print("DiscountShippingDestinationSelection:", ty.get("kind"),
      [p["name"] for p in ty.get("possibleTypes") or []])
for p in ty.get("possibleTypes") or []:
    r2 = c.graphql(
        "query T($n: String!) { __type(name: $n) { name fields { name type { name kind ofType { name kind } } } } }",
        {"n": p["name"]},
    )
    t2 = r2.get("__type") or {}
    print(f"  {p['name']}:")
    for f in t2.get("fields", []):
        t1 = f["type"]
        inner = t1.get("ofType") or {}
        print(f"    {f['name']}: {t1.get('name') or inner.get('name')} ({t1.get('kind') or inner.get('kind')})")
