# -*- coding: utf-8 -*-
"""favicon 上线：主题资产 → fileCreate 转存 → settings.favicon（传播重试）。"""
import json
import time
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
client = StoreService().get_client(1)

# 1. 传主题资产
with open("/tmp/favicon-estry.png", "rb") as f:
    b64 = __import__("base64").b64encode(f.read()).decode()
rest.request("PUT", f"themes/{TID}/assets.json", json_body={
    "asset": {"key": "assets/favicon-estry.png", "attachment": b64}})
time.sleep(20)
pub = rest.request("GET", f"themes/{TID}/assets.json",
                   params={"asset[key]": "assets/favicon-estry.png"})["asset"].get("public_url")
print("asset public_url:", bool(pub))

# 2. 转存文件库
r = client.graphql(
    "mutation($f:[FileCreateInput!]!){fileCreate(files:$f){files{id}userErrors{message}}}",
    {"f": [{"originalSource": pub, "contentType": "IMAGE"}]})
fc = r.get("fileCreate") or {}
if fc.get("userErrors"):
    print("fileCreate errors:", fc["userErrors"]); sys.exit(1)
print("fileCreate ok")

# 3. 写 settings（读改写回整体）
time.sleep(25)
for attempt in range(4):
    sd = rest.request("GET", f"themes/{TID}/assets.json",
                      params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
    data = json.loads(sd)
    cur = data.get("current")
    if isinstance(cur, str):
        cur = data["presets"][cur]
    cur["favicon"] = "shopify://shop_images/favicon-estry.png"
    rest.request("PUT", f"themes/{TID}/assets.json", json_body={
        "asset": {"key": "config/settings_data.json", "value": json.dumps(data, ensure_ascii=False)}})
    time.sleep(15)
    back = json.loads(rest.request("GET", f"themes/{TID}/assets.json",
                                   params={"asset[key]": "config/settings_data.json"})["asset"]["value"])
    b = back.get("current")
    if isinstance(b, str):
        b = back["presets"][b]
    v = b.get("favicon")
    print(f"attempt{attempt+1} favicon={v!r}")
    if v and "shop_images" in v:
        print("FAVICON SET OK")
        break
