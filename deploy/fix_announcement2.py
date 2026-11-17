# -*- coding: utf-8 -*-
"""公告条 v2：打印真实结构 → 精确改 → 回读验证 + menus 列表探测。"""
import json
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

store = StoreService().get_client(1)
cl = ShopifyRest(store).client

key = "sections/header-group.json"
a = cl.request("GET", "themes/190031036660/assets.json", params={"asset[key]": key})
grp = json.loads(a["asset"]["value"])
print("== sections 键:", list(grp.get("sections", {}).keys()))
for sid, blk in grp.get("sections", {}).items():
    print(f"   [{sid}] type={blk.get('type')} keys={list(blk.keys())}")
    for bid, b in (blk.get("blocks") or {}).items():
        print(f"      block[{bid}] type={b.get('type')} settings={b.get('settings')}")

NEW_TEXT = "12-Month Warranty · 30-Day Easy Returns · Ships from US in 48h"
changed = []
for sid, blk in grp.get("sections", {}).items():
    for bid, b in (blk.get("blocks") or {}).items():
        if b.get("type") == "announcement" and isinstance(b.get("settings"), dict) \
                and "text" in b["settings"]:
            b["settings"]["text"] = NEW_TEXT
            changed.append(f"{sid}/{bid}")
print("== 修改:", changed)
if changed:
    cl.request("PUT", "themes/190031036660/assets.json",
               json_body={"asset": {"key": key,
                                    "value": json.dumps(grp, ensure_ascii=False)}})
    a2 = cl.request("GET", "themes/190031036660/assets.json",
                    params={"asset[key]": key})
    ok = NEW_TEXT in a2["asset"]["value"]
    print("== 回读验证:", "新文案已生效" if ok else "仍为旧文案!")

# menus 列表探测（2025-01）
creds = cl.creds
headers = {"Accept": "application/json", "Content-Type": "application/json"}
if getattr(cl, "_token", None):
    headers["X-Shopify-Access-Token"] = cl._token
hc = httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/", timeout=30,
                  headers=headers, auth=cl._auth)
try:
    r = hc.post("graphql.json", json={"query":
        "query { menus(first: 20) { nodes { id title handle } } }"})
    out = r.json()
    if out.get("errors"):
        print("== menus:", str(out["errors"])[:180])
    else:
        print("== menus OK:", out["data"]["menus"]["nodes"])
except Exception as e:
    print("== menus 探测失败:", str(e)[:140])
