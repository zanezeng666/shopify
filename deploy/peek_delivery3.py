# -*- coding: utf-8 -*-
"""内省 DeliveryProfileInput / WeightInput / MoneyInput / 枚举。"""
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

for n in ("DeliveryProfileInput", "WeightInput", "MoneyInput"):
    intro(n)

for en in ("DeliveryConditionOperator", "WeightUnit"):
    q = '{ __type(name: "%s") { enumValues { name } } }' % en
    r = c.graphql(q) or {}
    t = r.get("__type") or {}
    print(f"== enum {en} == {[v['name'] for v in t.get('enumValues', [])]}\n")

# 读一个 zone 现有 methodDefinitions（应为空），确认查询形态
q = ('{ deliveryProfile(id: "gid://shopify/DeliveryProfile/25921388644") { '
     'id name profileType zones(first: 3) { edges { node { id name countries { code } '
     'methodDefinitions(first: 5) { edges { node { id name active '
     'rateProvider { __typename } } } } } } } } }')
r = c.graphql(q) or {}
import json
print(json.dumps(r, ensure_ascii=False)[:800])
