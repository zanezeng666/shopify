# -*- coding: utf-8 -*-
"""定位 /collections/medical-battery 页面上 Electronic Magnifier 等字样的渲染来源。"""
import re
import sys
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

# 1) API 侧：collection 描述/规则/模板
cols = []
for ep in ("smart_collections.json", "custom_collections.json"):
    cols += cl.request("GET", ep, params={"limit": 250}).get(ep.split(".")[0], [])
med = next(c for c in cols if c["handle"] == "medical-battery")
print("== API 视角 ==")
print("title:", med["title"])
print("description:", repr((med.get("description") or "")[:300]))
print("template_suffix:", med.get("template_suffix"))
print("published_scope:", med.get("published_scope"), "| sort_order:", med.get("sort_order"))

# 2) 线上页面：定位字样上下文
html = urllib.request.urlopen(
    "https://estrybattery.com/collections/medical-battery", timeout=30).read().decode("utf-8", "ignore")
print("\n== 线上页面字样上下文 ==")
for kw in ("Electronic Magnifier", "Shaver", "Thermal Electric"):
    for m in re.finditer(kw, html):
        s = max(0, m.start() - 260)
        ctx = html[s:m.end() + 120].replace("\n", " ")
        print(f"\n--- [{kw}] ---\n...{ctx}...")
        break  # 每词只看第一处
print("\n页面总长度:", len(html))
