# -*- coding: utf-8 -*-
"""MenuItemCreateInput 完整字段 + MenuItemType 枚举值。"""
import json
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
creds = cl.creds
headers = {"Accept": "application/json", "Content-Type": "application/json"}
if getattr(cl, "_token", None):
    headers["X-Shopify-Access-Token"] = cl._token
hc = httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/",
                  timeout=60, headers=headers, auth=cl._auth)

Q = """{ __type(name: "MenuItemCreateInput") {
  inputFields { name type { kind name ofType { kind name ofType { kind name } } } } } }"""
r = hc.post("graphql.json", json={"query": Q}).json()
for f in r["data"]["__type"]["inputFields"]:
    print(" ", f["name"], json.dumps(f["type"])[:110])
Q2 = """{ __type(name: "MenuItemType") { enumValues { name } } }"""
r2 = hc.post("graphql.json", json={"query": Q2}).json()
print("MenuItemType:", [v["name"] for v in r2["data"]["__type"]["enumValues"]])
