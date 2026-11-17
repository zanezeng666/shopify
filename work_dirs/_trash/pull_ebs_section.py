# -*- coding: utf-8 -*-
"""拉搜索 section 原文 + 定位搜索触发 JS 点。"""
import sys, re
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
KEY = "sections/estry-battery-search.liquid"
a = rest.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": KEY})["asset"]
v = a["value"]
open("/tmp/ebs_section.liquid", "w", encoding="utf-8").write(v)
print("bytes:", len(v))
# 找搜索函数与触发点
for m in re.finditer(r"(function\s+\w*[Ss]earch\w*|\.addEventListener\('(?:input|submit|click|keydown)'[^)]{0,60}|\.filter\w*\(|performSearch|onSearch|searchInput)", v):
    line_no = v[:m.start()].count("\n") + 1
    line = v.splitlines()[line_no - 1].strip()
    print(f"L{line_no}: {line[:110]}")
