# -*- coding: utf-8 -*-
"""终极定位：shop.description + Shaver 在页面所有出现位置。"""
import re
import sys
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

# 1) 商店描述
r = cl.graphql("{ shop { name description } }").get("shop", {})
print("shop.name:", r.get("name"))
print("shop.description:", repr(r.get("description")))

# 2) 页面正文里 Shaver 的全部出现（跳过 head 里的 meta）
req = urllib.request.Request(
    "https://estrybattery.com/collections/medical-battery",
    headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
body = html.split("</head>", 1)[-1]
print("\n== body 中 Shaver 出现位置 ==")
hits = list(re.finditer("Shaver", body))
print("总出现:", len(hits))
for m in hits[:6]:
    s = max(0, m.start() - 300)
    ctx = re.sub(r"\s+", " ", body[s:m.end() + 150])
    print(f"\n...{ctx}...")
