# -*- coding: utf-8 -*-
"""调试 metafield 写入：打印端点原始返回。"""
import sys
import json

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

PID = 15484753215732
cl = ShopifyRest(StoreService().get_client(1)).client

r1 = cl.request("POST", f"products/{PID}/metafields.json", json_body={
    "metafield": {"namespace": "seo", "key": "description",
                  "value": "debug probe", "type": "single_line_text_field"}})
print("POST resp:", json.dumps(r1, ensure_ascii=False)[:300])

r2 = cl.request("GET", f"products/{PID}/metafields.json", params={"namespace": "seo"})
print("GET by ns:", json.dumps(r2, ensure_ascii=False)[:300])

r3 = cl.request("GET", f"products/{PID}.json", params={"fields": "metafields"})
print("GET fields:", json.dumps(r3, ensure_ascii=False)[:300])
