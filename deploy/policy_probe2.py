# -*- coding: utf-8 -*-
"""introspect Shop 类型的政策字段 + 尝试政策更新。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

q = '{ __type(name: "Shop") { fields { name } } }'
g = c.graphql(q)
names = [f["name"] for f in (g.get("__type") or {}).get("fields", [])]
print("Shop 政策相关字段:", [n for n in names if "olic" in n or "terms" in n])

q2 = '{ __type(name: "QueryRoot") { fields { name } } }'
g2 = c.graphql(q2)
names2 = [f["name"] for f in (g2.get("__type") or {}).get("fields", [])]
print("QueryRoot 政策相关:", [n for n in names2 if "olic" in n.lower()])

# 若有 shopPolicies 之类就查 id
for cand in ("shopPolicies", "shopPoliciesV2"):
    if cand in names2:
        try:
            r = c.graphql("query { %s(first: 10) { nodes { id title handle } } }" % cand)
            print(cand, "→", r)
        except Exception as e:  # noqa: BLE001
            print(cand, "FAIL", str(e)[:150])

# mutation 侧
q3 = '{ __type(name: "Mutation") { fields { name } } }'
g3 = c.graphql(q3)
names3 = [f["name"] for f in (g3.get("__type") or {}).get("fields", [])]
print("Mutation 政策相关:", [n for n in names3 if "olic" in n])
