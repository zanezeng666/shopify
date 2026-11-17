# -*- coding: utf-8 -*-
"""运费配置终验：全部 zone methodDefinitions 读回断言。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

EXPECT = {"US": 4, "CA": 4, "MX": 1}
for cc in ["GB", "HU", "LV", "LT", "LU", "MT", "MC", "NL", "PL", "PT",
           "RO", "SK", "SI", "ES", "SE", "UA", "NO", "CH", "ZA", "GP",
           "NC", "PG", "LC", "VU"]:
    EXPECT[cc] = 3

c = StoreService().get_client(1)
zones = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
zmap = {}
for z in zones:
    cc = (z.get("countries") or [{}])[0].get("code")
    zmap[cc] = z.get("admin_graphql_api_id")

Q = """
query P($id: ID!) { deliveryProfile(id: $id) {
  profileLocationGroups {
    locationGroupZones(first: 100) { edges { node {
      zone { id name }
      methodDefinitions(first: 100) { edges { node {
        id name active
        rateProvider { __typename
          ... on DeliveryRateDefinition { price { amount } } }
      } } }
    } } }
  }
} }
"""
r = c.graphql(Q, {"id": "gid://shopify/DeliveryProfile/25921388644"}) or {}
gid2cc = {v: k for k, v in zmap.items()}
bad = 0
for lg in (r.get("deliveryProfile") or {}).get("profileLocationGroups", []):
    for e in lg.get("locationGroupZones", {}).get("edges", []):
        n = e["node"]
        cc = gid2cc.get(n["zone"]["id"])
        if cc is None:
            continue
        ms = [me["node"] for me in n["methodDefinitions"]["edges"]]
        rates = [(m["name"], m["active"],
                  (m.get("rateProvider") or {}).get("price", {}).get("amount"))
                 for m in ms]
        exp = EXPECT.get(cc)
        ok = len(rates) == exp and all(a for _, a, _ in rates)
        bad += not ok
        tag = "OK " if ok else "BAD"
        print(f"  {tag} {cc:3} {n['zone']['name']!r:22} n={len(rates)}/{exp}")
        if cc in ("US", "CA", "MX", "GB"):
            for nm, act, pr in rates:
                print(f"        ${pr:>5} {nm} (active={act})")
print(f"RESULT: {'全部通过' if bad == 0 else f'{bad} 个异常'}")
