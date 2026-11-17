# -*- coding: utf-8 -*-
"""wholesale 页 template_suffix + 主题 B2B section 清单 + 表单/询盘现状。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
p = rest.request("GET", "pages.json", params={"handle": "wholesale", "limit": 1})["pages"][0]
print("template_suffix:", p.get("template_suffix"))

ls = rest.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": "templates"}) if False else None
# 列 B2B 相关资产
assets = rest.request("GET", f"themes/{TID}/assets.json")["assets"]
names = [a["key"] for a in assets]
for n in names:
    if re.search(r"(wholesale|b2b|quote|wsi|inquir|contact)", n, re.I):
        print("ASSET:", n)
