# -*- coding: utf-8 -*-
"""写回搜索 section（GA4 埋点版）并回读断言。"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
KEY = "sections/estry-battery-search.liquid"
rest = ShopifyRest(StoreService().get_client(1)).client

v = open("/tmp/ebs_section_new.liquid", encoding="utf-8").read()
rest.request("PUT", f"themes/{TID}/assets.json", json_body={
    "asset": {"key": KEY, "value": v}})
print("PUT ok", len(v))

back = rest.request("GET", f"themes/{TID}/assets.json",
                    params={"asset[key]": KEY})["asset"]["value"]
for probe in ["ga4Search", "select_item", "search_term", 'data-m="']:
    print(probe, "PASS" if probe in back else "MISSING")
print("identical", back == v)
