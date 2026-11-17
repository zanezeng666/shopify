# -*- coding: utf-8 -*-
"""公告条文案落地 + 探测 2025-01 Navigation API 可用性。"""
import json
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

store = StoreService().get_client(1)
cl = ShopifyRest(store).client

# 1) 公告条：与详情页徽章同口径（_POLICY 实证，无虚假宣称）
NEW_TEXT = "12-Month Warranty · 30-Day Easy Returns · Ships from US in 48h"
key = "sections/header-group.json"
a = cl.request("GET", f"themes/190031036660/assets.json", params={"asset[key]": key})
grp = json.loads(a["asset"]["value"])
changed = 0
for blk in grp.get("sections", {}).values():
    if blk.get("type") == "announcement":
        for b in blk.get("blocks", {}).values() if "blocks" in blk else [blk]:
            st = b.get("settings", b) if "settings" not in b else b["settings"]
            if "text" in st:
                st["text"] = NEW_TEXT
                changed += 1
print("== 公告 block 修改数:", changed)
cl.request("PUT", "themes/190031036660/assets.json",
           json_body={"asset": {"key": key, "value": json.dumps(grp, ensure_ascii=False)}})
print("== 已回写", key)

# 2) 探测 2025-01 Navigation API（custom app 权限）
creds = store.creds if hasattr(store, "creds") else None
if creds is None:
    # ShopifyRest 包装的原始 client 持有 creds
    creds = cl.creds
headers = {"Accept": "application/json", "Content-Type": "application/json"}
if getattr(cl, "_token", None):
    headers["X-Shopify-Access-Token"] = cl._token
with httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/", timeout=30,
                  proxy=getattr(cl._client, "_transport") and None or None) as hc:
    pass  # proxy 不可直接复用，简单直连（服务器可直出）

hc = httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/", timeout=30,
                  headers=headers, auth=cl._auth)
try:
    r = hc.post("graphql.json", json={"query":
        'query { menu(handle: "main-menu") { id title itemsCount '
        "items { id title url items { id title url } } } }"})
    out = r.json()
    if out.get("errors"):
        print("== 2025-01 menu 读:", r.status_code, str(out["errors"])[:200])
    else:
        m = out["data"]["menu"]
        print("== 2025-01 menu 读 OK:", m["title"], "一级", len(m["items"]))
        for it in m["items"]:
            print("   -", it["title"], "子", len(it.get("items", [])))
except Exception as e:
    print("== 2025-01 探测失败:", str(e)[:150])
