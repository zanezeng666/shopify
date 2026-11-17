# -*- coding: utf-8 -*-
"""内省 deliveryProfileUpdate 签名与 rate/condition 输入类型。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)

def intro(name: str) -> None:
    q = ('{ __type(name: "%s") { inputFields { name '
         'type { kind name ofType { kind name ofType { kind name } } } } } }' % name)
    r = c.graphql(q) or {}
    t = r.get("__type")
    if not t:
        print(f"== {name}: 不存在\n")
        return
    print(f"== {name} ==")
    for f in t.get("inputFields", []):
        ty = f["type"]
        inner = ty.get("ofType") or {}
        inner2 = (inner.get("ofType") or {})
        print(f"  {f['name']}: {ty.get('kind')}<{ty.get('name')}>"
              f" -> {inner.get('kind')}<{inner.get('name')}>"
              f" -> {inner2.get('kind')}<{inner2.get('name')}>")
    print()

for n in ("DeliveryRateDefinitionInput", "DeliveryWeightConditionInput",
          "DeliveryPriceConditionInput", "DeliveryFixedRateInput",
          "DeliveryWeightRangeInput", "DeliveryPriceRangeInput",
          "DeliveryZoneInput"):
    intro(n)

print("== Mutation.deliveryProfileUpdate 签名 ==")
q = ('{ __schema { mutationType { fields { name args { name '
     'type { kind name ofType { kind name } } } } } } }')
r = c.graphql(q) or {}
for f in r["__schema"]["mutationType"]["fields"]:
    if "deliveryProfile" in f["name"] or "Delivery" in f["name"]:
        args = ", ".join(
            f"{a['name']}: {a['type'].get('name') or (a['type'].get('ofType') or {}).get('name')}"
            for a in f["args"])
        print(f"  {f['name']}({args})")
