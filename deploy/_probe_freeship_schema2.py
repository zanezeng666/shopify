# -*- coding: utf-8 -*-
"""探针2: destination 输入 + 读侧 DiscountAutomaticFreeShipping."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

Q_IN = ("query T($n: String!) { __type(name: $n) { name inputFields { name "
        "type { name kind ofType { name kind ofType { name kind } } } } } }")
Q_F = ("query T($n: String!) { __type(name: $n) { name fields { name "
       "type { name kind ofType { name kind ofType { name kind } } } } } }")

for tn in ("DiscountShippingDestinationSelectionInput", "DiscountCountriesInput"):
    r = c.graphql(Q_IN, {"n": tn})
    ty = r.get("__type") or {}
    fs = ty.get("inputFields") or []
    if not fs:
        print(f"{tn}: 不存在")
        continue
    print(f"{tn}:")
    for f in fs:
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
              f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'})")

# 读侧: 现有 discountNodes 里 FreeShipping 的查询形态（探 DiscountAutomaticFreeShipping 字段）
r = c.graphql(Q_F, {"n": "DiscountAutomaticFreeShipping"})
ty = r.get("__type") or {}
print("\nDiscountAutomaticFreeShipping (读侧):")
for f in ty.get("fields", []):
    t1, t2 = f["type"], (f["type"].get("ofType") or {})
    t3 = t2.get("ofType") or {}
    print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
          f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'})")
