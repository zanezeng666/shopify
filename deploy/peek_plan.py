# -*- coding: utf-8 -*-
"""查店铺 plan 与 CCS 状态、shipping zones 概览。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)

print("== shop plan ==")
r = c.graphql("""
{ shop { name myshopifyDomain
    plan { displayName partnerDevelopment shopifyPlus }
    enabledPresentmentCurrencies } }
""") or {}
print(r)

print("== carrier_services ==")
try:
    svcs = c.request("GET", "carrier_services.json").get("carrier_services", [])
    for s in svcs:
        print(f"  id={s['id']} name={s['name']!r} active={s.get('active')}")
    if not svcs:
        print("  (none)")
except Exception as e:  # noqa: BLE001
    print("  ERR", e)

print("== shipping zones (count) ==")
try:
    zs = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
    for z in zs:
        cs = [p["name"] for p in z.get("price_based_shipping_rates", [])]
        print(f"  zone={z['name']!r} countries={len(z.get('countries', []))} "
              f"price_rates={cs}")
except Exception as e:  # noqa: BLE001
    print("  ERR", e)
