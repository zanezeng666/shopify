# -*- coding: utf-8 -*-
"""只读：General profile 各 zone 现有 methodDefinitions 详情。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)
Q = """
query P($id: ID!) { deliveryProfile(id: $id) {
  profileLocationGroups {
    locationGroup { id }
    locationGroupZones(first: 100) { edges { node {
      zone { id name }
      methodDefinitions(first: 20) { edges { node { id name active
        description
        rateProvider { __typename }
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
        zn = n["zone"]
        for me in n.get("methodDefinitions", {}).get("edges", []):
            m = me["node"]
            print(f"  zone={zn['name']!r:24} method={m['name']!r:40} "
                  f"active={m.get('active')} provider={m.get('rateProvider')}")
