# -*- coding: utf-8 -*-
"""查第三方运费计算：carrier services + 已装应用。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)

print("== carrier_services ==")
try:
    svcs = c.request("GET", "carrier_services.json").get("carrier_services", [])
    for s in svcs:
        print(f"  id={s['id']} name={s['name']!r} active={s.get('active')}")
        print(f"    callback={s.get('carrier_service_type')}/{s.get('format')}"
              f" url={(s.get('admin_graphql_api_id') or '')[:0]}{s.get('service_discovery')}")
        print(f"    callback_url={s.get('callback_url')}")
except Exception as e:  # noqa: BLE001
    print("  ERR", e)

print("== appInstallations（含 shipping/carrier/rate 关键词）==")
q = """
{ apps(first: 50) {
    edges { node { title handle appStoreAppUrl pricing {
      ... on AppPricingOneTime { price } } } } } }
"""
try:
    r = c.graphql("{ apps(first: 50) { edges { node { title handle } } } }") or {}
    for e in r.get("apps", {}).get("edges", []):
        n = e["node"]
        print(f"  {n['handle']:30} {n['title']}")
except Exception as e:  # noqa: BLE001
    print("  ERR", e)
