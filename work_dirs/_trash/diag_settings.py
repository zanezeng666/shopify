# -*- coding: utf-8 -*-
"""诊断 settings_data.json 422：打印结构特征与完整错误体。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client

a = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                 params={"asset[key]": "config/settings_data.json"})["asset"]
v = a["value"]
sd = json.loads(v)
print("top keys:", list(sd.keys())[:10])
cur = sd.get("current")
print("current type:", type(cur).__name__, "| keys sample:", list(cur.keys())[:8] if isinstance(cur, dict) else str(cur)[:80])
print("has logo:", "logo" in cur if isinstance(cur, dict) else "-", "| logo now:", cur.get("logo") if isinstance(cur, dict) else "-")
print("logo_width now:", cur.get("logo_width") if isinstance(cur, dict) else "-")
print("len(value):", len(v))

# 试 PUT 原文不动（探测是否纯写入通道问题 vs 内容问题）
try:
    rest.request("PUT", f"themes/{THEME_ID}/assets.json", json_body={"asset": {"key": "config/settings_data.json", "value": v}})
    print("PUT original value: OK")
except Exception as e:
    print("PUT original value FAILED:", getattr(e, "message", str(e))[:400])
    body = getattr(e, "payload", None) or getattr(e, "details", None)
    print("err body:", body)
