# -*- coding: utf-8 -*-
"""GraphQL delivery profile 写入前探查：profile ID + 输入类型内省。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)

print("== REST zones -> profile/zone gid ==")
zones = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
for z in zones[:3] + zones[-1:]:
    print(f"  {z['name']!r:22} zone_gid={z.get('admin_graphql_api_id')} "
          f"profile={z.get('profile_id')} group={z.get('location_group_id')}")

def intro(name: str) -> None:
    q = ('{ __type(name: "%s") { inputFields { name '
         'type { kind name ofType { kind name ofType { kind name } } } } } }' % name)
    r = c.graphql(q) or {}
    t = r.get("__type")
    if not t:
        print(f"\n== {name}: 不存在 ==")
        return
    print(f"\n== {name} ==")
    for f in t.get("inputFields", []):
        ty = f["type"]
        inner = ty.get("ofType") or {}
        inner2 = (inner.get("ofType") or {})
        print(f"  {f['name']}: {ty.get('kind')}<{ty.get('name')}>"
              f" -> {inner.get('kind')}<{inner.get('name')}>"
              f" -> {inner2.get('kind')}<{inner2.get('name')}>")

for n in ("DeliveryProfileUpdateInput", "DeliveryZoneInput",
          "DeliveryMethodDefinitionInput", "DeliveryRateInput",
          "WeightBasedDeliveryRateInput", "DeliveryWeightConditionsInput",
          "DeliveryPriceConditionsInput", "DeliveryRatePriceInput"):
    intro(n)

print("\n== 顶层字段探测 ==")
r = c.graphql("{ deliveryProfiles(first: 5) { edges { node { id name } } } }") or {}
print(json.dumps(r)[:300])
