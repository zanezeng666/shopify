# -*- coding: utf-8 -*-
"""查店铺注册区域+当前支付网关，判断 Shopify Payments 可用路径。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
s = c.request("GET", "shop.json", params={
    "fields": "name,country_code,country_name,currency,plan_name,province,"
              "city,zip,primary_locale,domain"})
print("SHOP:", json.dumps(s.get("shop", s), ensure_ascii=False))

try:
    g = c.request("GET", "payment_gateways.json")
    for gw in g.get("payment_gateways", []):
        print("GW:", gw.get("gateway_type") or gw.get("type"), "|",
              (gw.get("name") or "")[:40], "| enabled=", gw.get("enabled"),
              "| card=", gw.get("processing_method"))
except Exception as e:  # noqa: BLE001
    print("payment_gateways FAIL:", str(e)[:120])
