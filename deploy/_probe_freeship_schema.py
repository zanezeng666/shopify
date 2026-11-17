# -*- coding: utf-8 -*-
"""探针: discountAutomaticFreeShippingCreate 的 2024-10 输入形态."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

Q_IN = ("query T($n: String!) { __type(name: $n) { name inputFields { name "
        "type { name kind ofType { name kind ofType { name kind } } } } } }")
Q_F = ("query T($n: String!) { __type(name: $n) { name fields { name "
       "type { name kind ofType { name kind ofType { name kind } } } } } }")
Q_U = "query T($n: String!) { __type(name: $n) { name kind possibleTypes { name } } }"


def dump(tn: str, q: str, key: str) -> list[str]:
    r = c.graphql(q, {"n": tn})
    ty = r.get("__type") or {}
    fs = ty.get(key) or []
    if not fs:
        print(f"\n{tn}: 不存在或无字段")
        return []
    print(f"\n{tn}:")
    for f in fs:
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
              f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'})")
    return [f["name"] for f in fs]


for tn in ("DiscountAutomaticFreeShippingInput", "DiscountCustomerGetsInput",
           "DiscountItemsInput", "DiscountFreeShippingDestinationInput",
           "DiscountCombinesWithInput", "DiscountMinimumRequirementInput"):
    dump(tn, Q_IN, "inputFields")

for tn in ("DiscountFreeShippingDestinations", "DiscountFreeShippingValue"):
    r = c.graphql(Q_U, {"n": tn})
    ty = r.get("__type") or {}
    print(f"\n{tn}: kind={ty.get('kind')} possible={[p['name'] for p in ty.get('possibleTypes') or []]}")
    if ty.get("kind") == "UNION":
        for p in ty["possibleTypes"]:
            dump(p["name"], Q_F, "fields")
