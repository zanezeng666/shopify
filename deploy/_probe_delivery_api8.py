# -*- coding: utf-8 -*-
"""探针8: connection edge 上找 methodDefinitions + DeliveryZone 再确认."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

for tn in ("DeliveryLocationGroupZoneEdge", "DeliveryLocationGroupZoneConnection"):
    r = c.graphql(
        "query T($n: String!) { __type(name: $n) { name fields { name type { name kind ofType { name kind ofType { name kind } } } } } }",
        {"n": tn},
    )
    ty = r.get("__type") or {}
    print(f"\n{tn}:")
    for f in ty.get("fields", []):
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
              f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'})")

# 真实数据: 带 methodDefinitions 的 edge
r = c.graphql("""{
  deliveryProfiles(first: 10) {
    nodes {
      id name default
      profileLocationGroups {
        locationGroup { id }
        locationGroupZones(first: 40) {
          edges {
            methodDefinitions(first: 10) {
              nodes {
                id name
                rateProvider { __typename ... on DeliveryRateDefinition { price { amount currencyCode } } }
                conditions(first: 5) {
                  nodes {
                    __typename
                    ... on DeliveryWeightCondition { weight { value unit } operator }
                    ... on DeliveryPriceCondition { price { amount } operator }
                  }
                }
              }
            }
            node { zone { id name countries { code { code } } } }
          }
        }
      }
    }
  }
}""")
print("\n===== 真实数据 =====")
for p in r.get("deliveryProfiles", {}).get("nodes", []):
    print(f"\nprofile: {p.get('name') or '(general)'} default={p.get('default')} {p['id']}")
    for lg in p.get("profileLocationGroups", []):
        grp = lg.get("locationGroup") or {}
        edges = (lg.get("locationGroupZones") or {}).get("edges", [])
        print(f"  locationGroup {grp.get('id')} zones={len(edges)}")
        for e in edges:
            zone = (e.get("node") or {}).get("zone") or {}
            codes = [cc["code"]["code"] for cc in (zone.get("countries") or [])]
            if "US" in codes:
                print(f"    *** US zone {zone['id']} [{zone.get('name')}]")
                for m in (e.get("methodDefinitions") or {}).get("nodes", []):
                    rp = m.get("rateProvider") or {}
                    price = (rp.get("price") or {}).get("amount")
                    conds = (m.get("conditions") or {}).get("nodes", [])
                    parts = []
                    for cn in conds:
                        w, pr = cn.get("weight"), cn.get("price")
                        if w:
                            parts.append(f"{cn['__typename'].replace('Delivery','').replace('Condition','')}{cn.get('operator','')} {w.get('value')}{w.get('unit')}")
                        elif pr:
                            parts.append(f"{cn['__typename'].replace('Delivery','').replace('Condition','')}{cn.get('operator','')} ${pr.get('amount')}")
                    print(f"      - {m['name']} ${price} [{' ; '.join(parts)}] ({m['id']})")
