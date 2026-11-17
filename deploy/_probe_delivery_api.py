# -*- coding: utf-8 -*-
"""探针: deliveryProfileUpdate 是否可改运费规则 (只读探 schema, 不改任何数据)."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client


def t(name: str) -> dict:
    r = c.graphql(
        "query T($n: String!) { __type(name: $n) { name inputFields { name type { name kind ofType { name kind } } } } }",
        {"n": name},
    )
    return r.get("__type") or {}


def show(name: str) -> None:
    ty = t(name)
    if not ty:
        print(f"{name}: 不存在")
        return
    print(f"\n{name}:")
    for f in ty.get("inputFields", []):
        tt = f["type"]
        inner = tt.get("ofType") or {}
        print(f"  {f['name']}: {tt.get('name') or inner.get('name')} "
              f"({tt.get('kind') or inner.get('kind')})")


# 1. mutation 是否存在
r = c.graphql(
    "{ __schema { mutationType { fields { name } } } }"
)
muts = [f["name"] for f in r["__schema"]["mutationType"]["fields"] if "delivery" in f["name"].lower()]
print("[1] delivery 相关 mutation:", muts)

# 2. 关键输入类型结构
for name in ("DeliveryProfileUpdateInput", "DeliveryZoneInput", "DeliveryCountryInput",
             "DeliveryPriceBasedShippingRateInput", "DeliveryWeightBasedShippingRateInput"):
    show(name)

# 3. 查现有 profiles + zones
r = c.graphql("""{
  deliveryProfiles(first: 10) {
    nodes {
      id
      name
      profileDefault { zones(first: 30) { nodes { id name countries { code { code } } } } }
      zones(first: 30) { nodes { id name countries { code { code } } } }
    }
  }
}""")
print("\n[3] deliveryProfiles:")
for p in r.get("deliveryProfiles", {}).get("nodes", []):
    zs = (p.get("profileDefault") or {}).get("zones", {}).get("nodes", []) or p.get("zones", {}).get("nodes", [])
    print(f"  profile {p.get('name') or '(default)'} {p['id']} zones={len(zs)}")
    for z in zs:
        codes = [cc["code"]["code"] for cc in (z.get("countries") or [])]
        if "US" in codes:
            print(f"    *** US zone: {z['id']} [{z.get('name')}] codes={codes}")
        elif len(codes) <= 3:
            print(f"    zone {z['id']} [{z.get('name')}] codes={codes}")
