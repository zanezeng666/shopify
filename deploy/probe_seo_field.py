# -*- coding: utf-8 -*-
"""GraphQL 查 collection.seo（REST 不可见的 SEO listing 存储）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

Q = """{
  collections(first: 100) {
    nodes { handle seo { title description } }
  }
}"""
r = cl.graphql(Q).get("collections", {}).get("nodes", [])
for c in r:
    if c["handle"] == "medical-battery":
        print("== medical-battery ==")
        print("seo:", c.get("seo"))
# 顺带统计全店 seo description 非空且含类目清单字样的
print("\n== 全店 seo.description 含可疑类目串 ==")
for c in r:
    d = (c.get("seo") or {}).get("description") or ""
    if d and any(k in d for k in ("Magnifier", "Thermal Electric", "Toothbrush", "Microscope")):
        print(" ", c["handle"], "->", d[:120])
