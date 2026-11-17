# -*- coding: utf-8 -*-
"""抽验 5 条旧源死链 link 的 handle 在 Shopify 是否真的不存在。"""
import json
import urllib.parse

from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

d = json.load(open("/home/jason/shopify-admin/deploy/mc_purge_state2.json"))
client = ShopifyRest(StoreService().get_client(1)).client

sample = d["dead_olddsr"][:5] + d["dead_olddsr"][-3:]
bad = 0
for p in sample:
    handle = urllib.parse.urlparse(p["link"]).path.rsplit("/", 1)[-1]
    r = client.request("GET", "products.json", params={"handle": handle})
    items = r if isinstance(r, list) else r.get("products", [])
    if not items:
        print(f"✓ 商品已彻底删除 {handle[:52]}")
    else:
        st = items[0].get("status")
        if st == "active":
            bad += 1
            print(f"✗✗ ACTIVE 在售!误判风险 {handle[:52]}")
        else:
            print(f"✓ {st}(前台404=死链成立) {handle[:44]}")
print(f"\nactive 误判数: {bad}/8")

