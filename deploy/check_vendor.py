# -*- coding: utf-8 -*-
"""抽查线上 vendor 是否已是 Estry (MC feed brand 取自 vendor, 红线检查)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from collections import Counter

from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
c = Counter()
for vid in (8736844657111, 8736844788183):   # 抽前两页样例
    pass
r = cl._client.get("products/count.json", auth=cl._auth,
                   params={"vendor": "Cameron Sino", "status": "active"},
                   timeout=30)
cs_cnt = r.json().get("count", -1)
r2 = cl._client.get("products/count.json", auth=cl._auth,
                    params={"vendor": "Estry", "status": "active"},
                    timeout=30)
e_cnt = r2.json().get("count", -1)
print(f"线上 ACTIVE vendor=Cameron Sino: {cs_cnt}")
print(f"线上 ACTIVE vendor=Estry: {e_cnt}")
