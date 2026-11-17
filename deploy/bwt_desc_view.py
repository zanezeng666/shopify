# -*- coding: utf-8 -*-
"""修复 /collections/all 缺 meta description：theme.liquid 条件输出。改前备份。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client
KEY = "layout/theme.liquid"

a = cl.request("GET", "themes/190031036660/assets.json",
               params={"asset[key]": KEY})
src = a["asset"]["value"]
i = src.find("page_description")
print("== theme.liquid description 段 ==")
print(src[max(0, i - 250): i + 300])
