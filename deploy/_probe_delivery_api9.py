# -*- coding: utf-8 -*-
"""探针9: includeDeprecated 重探 + 国家字段形态."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

for tn in ("DeliveryProfileLocationGroup", "DeliveryLocationGroupZone",
           "DeliveryLocationGroupZoneEdge", "DeliveryCountryCodeOrRestOfWorld"):
    r = c.graphql(
        "query T($n: String!) { __type(name: $n) { name "
        "fields(includeDeprecated: true) { name isDeprecated deprecationReason "
        "type { name kind ofType { name kind ofType { name kind } } } } } }",
        {"n": tn},
    )
    ty = r.get("__type") or {}
    print(f"\n{tn}:")
    for f in ty.get("fields", []):
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        dep = " [DEPRECATED]" if f.get("isDeprecated") else ""
        print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
              f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'}){dep}")
