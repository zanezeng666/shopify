# -*- coding: utf-8 -*-
"""探测 menuUpdate 原始响应，定位 KeyError data 的原因。"""
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

# 只读查询试水：menu 是否可见
q = """{ menu(id: "gid://shopify/Menu/59300577380") {
  id title items { id title } } }"""
r = hc.post("graphql.json", json={"query": q})
print("status:", r.status_code)
print(r.text[:600])
