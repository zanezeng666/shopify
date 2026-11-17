# -*- coding: utf-8 -*-
"""探针3: DeliveryProfileInput 输入链 + 真实 profile 数据 (找美国 zone 与 rate)."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client


def fields_of(type_name: str) -> list[tuple[str, str, str]]:
    r = c.graphql(
        "query T($n: String!) { __type(name: $n) { name kind "
        "inputFields { name type { name kind ofType { name kind ofType { name kind } } } } "
        "fields { name type { name kind ofType { name kind ofType { name kind } } } } } }",
        {"n": type_name},
    )
    ty = r.get("__type") or {}
    out = []
    for f in (ty.get("inputFields") or ty.get("fields") or []):
        t1, t2 = f["type"], (f["type"].get("ofType") or {})
        t3 = t2.get("ofType") or {}
        out.append((f["name"], t1.get("name") or t2.get("name") or t3.get("name") or "?",
                    t1.get("kind") or t2.get("kind") or t3.get("kind") or "?"))
    return out, ty.get("kind")


for tn in ("DeliveryProfileInput", "DeliveryLocationGroupInput" if True else "",
           "DeliveryZoneInput", "DeliveryShippingRateInput",
           "DeliveryPriceBasedShippingRateInput", "DeliveryWeightBasedShippingRateInput"):
    fs, kind = fields_of(tn)
    if not fs:
        print(f"\n{tn}: 不存在")
        continue
    print(f"\n{tn} ({kind}):")
    for n, t, k in fs:
        print(f"  {n}: {t} ({k})")
