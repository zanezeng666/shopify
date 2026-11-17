# -*- coding: utf-8 -*-
"""探针4: DeliveryProfileLocationGroupInput 输入链 + 真实数据 (美国 zone GID + rates)."""
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


for tn in ("DeliveryProfileLocationGroupInput", "DeliveryZoneGroupsInput", "DeliveryZoneGroupInput"):
    fields_of(tn)

# 真实数据: general profile 的 location groups -> zones -> rates
r = c.graphql("""{
  deliveryProfiles(first: 10) {
    nodes {
      id name default version
      profileLocationGroups(first: 5) {
        nodes {
          locationGroup { id name }
          zones(first: 40) {
            nodes {
              id name
              countries { code { code } }
              priceBasedShippingRates(first: 10) { nodes { id name amount } }
              weightBasedShippingRates(first: 10) {
                nodes { id name amount weightLow weightHigh weightUnit }
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
    for lg in p.get("profileLocationGroups", {}).get("nodes", []):
        grp = lg.get("locationGroup") or {}
        zones = lg.get("zones", {}).get("nodes", [])
        print(f"  locationGroup: {grp.get('name')} {grp.get('id')} zones={len(zones)}")
        for z in zones:
            codes = [cc["code"]["code"] for cc in (z.get("countries") or [])]
            pr = z.get("priceBasedShippingRates", {}).get("nodes", [])
            wr = z.get("weightBasedShippingRates", {}).get("nodes", [])
            mark = " *** US ***" if "US" in codes else ""
            print(f"    zone {z['id']} [{z.get('name')}] {len(codes)}国{mark}")
            for x in pr:
                print(f"      price-rate: {x['name']} ${x['amount']} ({x['id']})")
            for x in wr:
                print(f"      weight-rate: {x['name']} ${x['amount']} {x.get('weightLow')}~{x.get('weightHigh')}{x.get('weightUnit')} ({x['id']})")
