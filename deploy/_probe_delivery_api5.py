# -*- coding: utf-8 -*-
"""探针5: DeliveryLocationGroupZoneInput + methodDefinition 输入链 + 真实数据."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client


def fields_of(type_name: str) -> None:
    r = c.graphql(
        "query T($n: String!) { __type(name: $n) { name kind "
        "inputFields { name type { name kind ofType { name kind ofType { name kind } } } } "
        "fields { name type { name kind ofType { name kind ofType { name kind } } } } } }",
        {"n": type_name},
    )
    ty = r.get("__type") or {}
    fs = ty.get("inputFields") or ty.get("fields") or []
    if not fs:
        print(f"\n{type_name}: 不存在")
        return
    print(f"\n{type_name} ({ty.get('kind')}):")
    for f in fs:
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
              f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'})")


for tn in ("DeliveryLocationGroupZoneInput", "DeliveryShippingMethodDefinitionInput",
           "DeliveryConditionInput", "DeliveryPriceConditionInput", "DeliveryWeightConditionInput",
           "DeliveryRateDefinitionInput"):
    fields_of(tn)

# 真实数据: profileLocationGroups 是直接的 list, zones 是否带 first 参数待试
r = c.graphql("""{
  deliveryProfiles(first: 10) {
    nodes {
      id name default version
      profileLocationGroups {
        locationGroup { id name }
        zones(first: 40) {
          nodes {
            id name
            countries { code { code } }
            methodDefinitions(first: 10) {
              nodes { id name description
                rateProvider { ... on DeliveryRateDefinition { price { amount currencyCode } } }
                conditions(first: 5) { nodes { __typename ... on DeliveryWeightCondition { weight { value unit } } ... on DeliveryPriceCondition { price { amount } } } }
              }
            }
          }
        }
      }
    }
  }
}""")
print("\n===== 真实数据 =====")
for p in r.get("deliveryProfiles", {}).get("nodes", []):
    print(f"\nprofile: {p.get('name') or '(general)'} default={p.get('default')} {p['id']} v{p.get('version')}")
    for lg in p.get("profileLocationGroups", []):
        grp = lg.get("locationGroup") or {}
        zones = (lg.get("zones") or {}).get("nodes", [])
        print(f"  locationGroup: {grp.get('name')} {grp.get('id')} zones={len(zones)}")
        for z in zones:
            codes = [cc["code"]["code"] for cc in (z.get("countries") or [])]
            mds = (z.get("methodDefinitions") or {}).get("nodes", [])
            if "US" in codes:
                print(f"    *** US zone {z['id']} [{z.get('name')}]")
                for m in mds:
                    price = ((m.get("rateProvider") or {}).get("price") or {})
                    conds = (m.get("conditions") or {}).get("nodes", [])
                    cond_s = "; ".join(
                        f"{cn.get('__typename')}={cn.get('weight') or cn.get('price')}" for cn in conds)
                    print(f"      - {m['name']} ${price.get('amount')} {cond_s} ({m['id']})")
