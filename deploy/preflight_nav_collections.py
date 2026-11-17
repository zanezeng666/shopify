# -*- coding: utf-8 -*-
"""摸底 v4：本地库 product_type 分布 / 首页导航两级结构 / 公告条实例配置。"""
import re
import sys

import httpx
from sqlalchemy import text

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.core.database import get_engine
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

# 1) product_type 全量分布（本地库镜像）
with get_engine().connect() as cx:
    rows = cx.execute(text(
        "SELECT product_type, COUNT(*) c FROM products "
        "WHERE store_id=1 GROUP BY product_type ORDER BY c DESC")).fetchall()
print(f"== product_type 共 {len(rows)} 种（Top 30）:")
for t, c in rows[:30]:
    print(f"   {t!r:42} {c}")
med = [r for r in rows if r[0] and "medic" in r[0].lower()]
print("== Medical 相关:", med)

# 2) 首页导航：header 内 details/summary 两级结构
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
html = httpx.get("https://estrybattery.com/", headers=UA, follow_redirects=True,
                 timeout=30).text
hdr = re.search(r"<header.*?</header>", html, re.S)
h = hdr.group(0) if hdr else html
print("== 导航（summary 一级 / 其后 collections 二级）:")
for det in re.findall(r"<details[^>]*>(.*?)</details>", h, re.S):
    sm = re.search(r"<summary[^>]*>(.*?)</summary>", det, re.S)
    if not sm:
        continue
    top = re.sub(r"<[^>]+>", " ", sm.group(1)).split()
    subs = []
    for href, inner in re.findall(
            r'<a[^>]*href="(/collections/[^"]+)"[^>]*>(.*?)</a>', det, re.S):
        txt = " ".join(re.sub(r"<[^>]+>", " ", inner).split())
        subs.append(f"{txt}[{href.split('/')[-1]}]")
    if top and subs:
        print(f"   L1 {' '.join(top)!r} -> {len(subs)} 项: {subs}")

# 3) 公告条实例配置（header group JSON）
cl = ShopifyRest(StoreService().get_client(1)).client
for key in ("sections/header-group.json", "config/settings_data.json"):
    a = cl.request("GET", "themes/190031036660/assets.json",
                   params={"asset[key]": key})
    v = a["asset"]["value"]
    i = v.find("Welcome")
    print(f"== {key}: {'含 Welcome @' + str(i) if i >= 0 else '无'}")
    if i >= 0:
        print("   ", v[max(0, i - 80):i + 60].replace("\n", " "))
