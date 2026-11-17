# -*- coding: utf-8 -*-
"""只读统计: active产品变体总数(UPC需求量)、无价格/无SKU变体数。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

QUERY = """query($c: String) {
  products(query: "status:active", first: 250, after: $c) {
    nodes { id
      variants(first: 100) { nodes { price sku } } }
    pageInfo { hasNextPage endCursor } } }"""

cursor = None
prods = variants = noprice = nosku = 0
while True:
    time.sleep(0.8)
    r = cl._client.post(
        f"{cl._client.base_url}/graphql.json", auth=cl._auth,
        json={"query": QUERY, "variables": {"c": cursor}}, timeout=60)
    data = r.json()["data"]["products"]
    for p in data["nodes"]:
        prods += 1
        for v in p["variants"]["nodes"]:
            variants += 1
            if not v["price"] or float(v["price"] or 0) <= 0:
                noprice += 1
            if not v["sku"]:
                nosku += 1
    if not data["pageInfo"]["hasNextPage"]:
        break
    cursor = data["pageInfo"]["endCursor"]

print(f"active 产品数: {prods}")
print(f"active 变体总数(UPC需求量): {variants}")
print(f"其中无价格变体: {noprice}")
print(f"其中无SKU变体: {nosku}")
