# -*- coding: utf-8 -*-
"""诊断 shipping zone PUT 406：三种 body 变体直试，打印响应体。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)
ZID = 44532236388
zones = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
z = next(x for x in zones if x["id"] == ZID)
rates_w = [{"name": "Standard Shipping (3-6 business days), 0kg-1kg",
            "price": "5.99", "weight_low": 0, "weight_high": 1}]

variants = [
    ("A 仅 id+code countries", {"shipping_zone": {
        "id": ZID, "name": z["name"],
        "countries": [{"id": ct["id"], "code": ct["code"]}
                      for ct in z["countries"]],
        "weight_based_shipping_rates": rates_w}}),
    ("B 不带 countries", {"shipping_zone": {
        "id": ZID,
        "weight_based_shipping_rates": rates_w}}),
    ("C 带 name 不带 countries", {"shipping_zone": {
        "id": ZID, "name": z["name"],
        "weight_based_shipping_rates": rates_w}}),
]

import httpx
from shopify_admin.core.exceptions import ShopifyAPIError

for label, body in variants:
    try:
        r = c.request("PUT", f"shipping_zones/{ZID}.json", json_body=body)
        print(f"{label}: OK keys={list(r.get('shipping_zone', {}).keys())[:6]}")
        break
    except ShopifyAPIError as e:
        det = getattr(e, "details", None) or {}
        err = det.get("errors")
        print(f"{label}: FAIL {det.get('status')} {str(err)[:200]}")

# D: form-encoded（shipping_zones 端点历史怪癖）
print("D form-encoded:")
try:
    import httpx as _hx
    resp = c._client.request(
        "PUT", f"shipping_zones/{ZID}.json",
        data={"shipping_zone": json.dumps(body["shipping_zone"])},
        auth=c._auth)
    print(f"  status={resp.status_code} body={resp.text[:200]}")
except Exception as e:  # noqa: BLE001
    print("  EXC", e)
