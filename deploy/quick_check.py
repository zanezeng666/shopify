# -*- coding: utf-8 -*-
"""快查: 抽样Google渠道状态 + barcode已清空比例(中间态)。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

# 1) Google 渠道连通性
r = cl._client.post(
    f"{cl._client.base_url}/graphql.json", auth=cl._auth,
    json={"query": "{ publications(first: 20) { nodes { name "
          "catalog { id } } } }"}, timeout=60)
chn = [n["name"] for n in r.json()["data"]["publications"]["nodes"]]
print("渠道:", "Google & YouTube 在列" if any(
    "google" in n.lower() for n in chn) else "缺失", chn)

# 2) 抽样第一页 250 产品: barcode 空置率
r2 = cl._client.get("products.json", auth=cl._auth, params={
    "limit": 250, "status": "active", "fields": "id,variants"},
    timeout=60)
total = has_bc = 0
for p in r2.json()["products"]:
    for v in p["variants"]:
        total += 1
        if v.get("barcode"):
            has_bc += 1
print(f"抽样(首页250品): 变体 {total} 个, 仍带条码 {has_bc} 个 "
      f"({has_bc * 100 // max(total, 1)}%)")
