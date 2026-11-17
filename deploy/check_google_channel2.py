# -*- coding: utf-8 -*-
"""Google 渠道产品总数 + 发布状态分布。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

def gql(q, v=None):
    r = cl._client.post(f"{cl._client.base_url}/graphql.json", auth=cl._auth,
                        json={"query": q, "variables": v or {}}, timeout=60)
    return r.json()

# 用 productCount 字段
r = gql("""{ publications(first: 20) {
  nodes { id name
    products(first: 1) { productCount } } } }""")
if r.get("errors"):
    print("productCount 不可用:", str(r["errors"])[:150])
    # 回退: 数 status
    r = gql("""{ publications(first: 20) {
      nodes { id name products(first: 250) { edges { node { id } }
      pageInfo { hasNextPage } } } } }""")
    for n in r.get("data", {}).get("publications", {}).get("nodes", []):
        cnt = len(n["products"]["edges"])
        more = "+" if n["products"]["pageInfo"]["hasNextPage"] else ""
        g = " <<<GOOGLE" if "google" in n["name"].lower() else ""
        print(f"渠道: {n['name']:<30} 产品>={cnt}{more}{g}")
else:
    for n in r["data"]["publications"]["nodes"]:
        cnt = n["products"]["productCount"]
        g = " <<<GOOGLE" if "google" in n["name"].lower() else ""
        print(f"渠道: {n['name']:<30} 产品数={cnt}{g}")

# Google 渠道产品当前状态分布(取第一页看 status)
r2 = gql("""{ publications(first: 20) {
  nodes { name products(first: 3) { nodes { title
    resourcePublicationOnCurrentPublication { isPublished } } } } } }""")
for n in r2.get("data", {}).get("publications", {}).get("nodes", []):
    if "google" in n["name"].lower():
        print("\nGoogle 渠道前3品发布态:")
        for p in n["products"]["nodes"]:
            pub = p.get("resourcePublicationOnCurrentPublication") or {}
            print(f"  isPublished={pub.get('isPublished')} | {p['title'][:50]}")
