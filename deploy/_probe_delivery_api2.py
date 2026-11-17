# -*- coding: utf-8 -*-
"""探针2: 从 mutation 签名与 DeliveryProfile 字段反推 delivery API 结构."""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client


def gql(q, v=None):
    return c.graphql(q, v or {})


def show_type(name: str, depth_field="inputFields") -> None:
    r = gql("query T($n: String!) { __type(name: $n) { name "
            + (f"{depth_field} {{ name type {{ name kind ofType {{ name kind }} }} }}" if depth_field else "kind")
            + " } }", {"n": name})
    ty = r.get("__type") or {}
    if not ty:
        print(f"{name}: 不存在")
        return
    print(f"\n{name} ({ty.get('kind')}):")
    for f in ty.get(depth_field, []):
        t1 = f["type"]
        inner = t1.get("ofType") or {}
        print(f"  {f['name']}: {t1.get('name') or inner.get('name')} "
              f"({t1.get('kind') or inner.get('kind')})")


# 1. deliveryProfileUpdate 签名
r = gql("""query {
  __type(name: "Mutation") {
    fields(includeDeprecated: true) {
      name args { name type { name kind ofType { name kind ofType { name kind } } } }
    }
  }
}""")
for f in r["__type"]["fields"]:
    if f["name"] == "deliveryProfileUpdate":
        print("[1] deliveryProfileUpdate args:")
        for a in f["args"]:
            t1 = a["type"]
            t2 = t1.get("ofType") or {}
            t3 = (t2.get("ofType") or {})
            print(f"  {a['name']}: {t1.get('name') or t2.get('name') or t3.get('name')}")
        break

# 2. DeliveryProfile 字段
r = gql("""query {
  __type(name: "DeliveryProfile") {
    fields { name type { name kind ofType { name kind ofType { name } } } }
  }
}""")
print("\n[2] DeliveryProfile 字段:")
for f in r["__type"]["fields"]:
    t1 = f["type"]
    t2 = t1.get("ofType") or {}
    t3 = t2.get("ofType") or {}
    print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name')} ({t1.get('kind') or t2.get('kind')})")
