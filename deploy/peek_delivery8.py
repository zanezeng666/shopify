# -*- coding: utf-8 -*-
"""读 USA/MX/UK/CA zone 现有 method 的价格与条件。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)
Q = """
query P($id: ID!) { deliveryProfile(id: $id) {
  profileLocationGroups {
    locationGroupZones(first: 100) { edges { node {
      zone { id name }
      methodDefinitions(first: 20) { edges { node { id name active
        rateProvider { __typename
          ... on DeliveryRateDefinition {
            price { amount currencyCode }
          }
        }
      } } }
    } } }
  }
} }
"""
r = c.graphql(Q, {"id": "gid://shopify/DeliveryProfile/25921388644"}) or {}
import json
for lg in (r.get("deliveryProfile") or {}).get("profileLocationGroups", []):
    for e in lg.get("locationGroupZones", {}).get("edges", []):
        n = e["node"]
        zn = n["zone"]["name"]
        if zn not in ("TO USA", "Mexico_Zone", "United Kingdom", "Canada"):
            continue
        for me in n.get("methodDefinitions", {}).get("edges", []):
            m = me["node"]
            rp = m.get("rateProvider") or {}
            price = (rp.get("price") or {})
            print(f"{zn:14} {m['name']!r:24} active={m['active']} "
                  f"price={price.get('amount')} {price.get('currencyCode')}")
