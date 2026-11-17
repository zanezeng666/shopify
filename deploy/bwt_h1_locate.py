# -*- coding: utf-8 -*-
"""定位空 h1 来源：首页 HTML h1 上下文 + header.liquid else 段。只读。"""
import re
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"}
r = httpx.get("https://www.estrybattery.com/", headers=UA, timeout=30,
              follow_redirects=True)
html = r.text
m = re.search(r"<h1[^>]*>.*?</h1>", html, re.S)
if m:
    s = max(0, m.start() - 400)
    print("== 首页 h1 前后上下文 ==")
    print(html[s:m.end() + 100])

cl = ShopifyRest(StoreService().get_client(1)).client
a = cl.request("GET", "themes/190031036660/assets.json",
               params={"asset[key]": "sections/header.liquid"})
src = a["asset"]["value"]
i = src.find("header__heading-text")
print("\n== header.liquid shop.name 分支 ==")
print(src[max(0, i - 300): i + 200])
