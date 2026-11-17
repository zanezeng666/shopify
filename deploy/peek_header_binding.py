# -*- coding: utf-8 -*-
"""查主题 header section 绑定的菜单 + 各菜单当前内容对比。"""
import json
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
a = cl.request("GET", "themes/190031036660/assets.json",
               params={"asset[key]": "sections/header-group.json"})
grp = json.loads(a["asset"]["value"])
print("== header section settings:",
      json.dumps(grp["sections"]["header"].get("settings", {}), ensure_ascii=False)[:400])

creds = cl.creds
headers = {"Accept": "application/json", "Content-Type": "application/json"}
if getattr(cl, "_token", None):
    headers["X-Shopify-Access-Token"] = cl._token
hc = httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/",
                  timeout=60, headers=headers, auth=cl._auth)
Q = """query($id: ID!) { menu(id: $id) {
  title handle items { title items { title } } } }"""
for gid, tag in (("gid://shopify/Menu/276472070388", "estry-main-menu"),
                 ("gid://shopify/Menu/195001975028", "main-menu-1"),
                 ("gid://shopify/Menu/59300577380", "main-menu(已改)")):
    r = hc.post("graphql.json", json={"query": Q, "variables": {"id": gid}}).json()
    m = (r.get("data") or {}).get("menu")
    if m:
        print(f"== {tag}: {m['title']} handle={m['handle']} 一级:",
              [(i["title"], len(i.get("items", []))) for i in m["items"]][:9])
