# -*- coding: utf-8 -*-
"""探针11: 全部 Delivery*Input 完整字段 + LegacyModeBlocked 枚举 + deliverySetting."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

INPUTS = ["DeliveryCountryInput", "DeliveryProvinceInput", "DeliveryLocationGroupZoneInput",
          "DeliveryProfileLocationGroupInput", "DeliveryProfileInput", "DeliveryRateDefinitionInput",
          "DeliveryPriceConditionInput", "DeliveryWeightConditionInput", "DeliveryUpdateConditionInput",
          "DeliverySettingInput", "DeliveryParticipantInput", "DeliveryParticipantServiceInput"]
for tn in INPUTS:
    r = c.graphql(
        "query T($n: String!) { __type(name: $n) { name inputFields { name "
        "type { name kind ofType { name kind ofType { name kind } } } } } }",
        {"n": tn},
    )
    ty = r.get("__type") or {}
    if not ty:
        print(f"\n{tn}: 不存在")
        continue
    print(f"\n{tn}:")
    for f in ty.get("inputFields", []):
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        print(f"  {f['name']}: {t1.get('name') or t2.get('name') or t3.get('name') or '?'} "
              f"({t1.get('kind') or t2.get('kind') or t3.get('kind') or '?'})")

# legacy 枚举值
for tn in ("DeliveryLegacyModeBlockedReason",):
    r = c.graphql("query T($n: String!) { __type(name: $n) { name enumValues { name } } }", {"n": tn})
    print(f"\n{tn}: {[v['name'] for v in (r['__type'] or {}).get('enumValues', [])]}")

# deliverySetting 读侧
r = c.graphql("{ deliverySetting { id legacyModeBlocked { blocked reasons } } }")
print("\ndeliverySetting:", r)
