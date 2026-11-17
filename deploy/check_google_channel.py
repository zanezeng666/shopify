# -*- coding: utf-8 -*-
"""验证 Google & YouTube channel app 的实际同步状态。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

def gql(q, v=None):
    r = cl._client.post(f"{cl._client.base_url}/graphql.json", auth=cl._auth,
                        json={"query": q, "variables": v or {}}, timeout=30)
    return r.json()

# 1) 所有 publication 渠道 + 各渠道产品数
r = gql("""{ publications(first: 20) {
  nodes { id name autoPublish
    products(first: 1) { totalCount } } } }""")
for n in r.get("data", {}).get("publications", {}).get("nodes", []):
    cnt = n["products"]["totalCount"]
    flag = " <<<" if "google" in n["name"].lower() else ""
    print(f"渠道: {n['name']:<28} 自动发布={n['autoPublish']} "
          f"产品数={cnt}{flag}")

# 2) 已安装 app 列表(找 Google channel)
r2 = gql("{ apps(first: 30) { nodes { title handle } } }")
apps = r2.get("data", {}).get("apps", {}).get("nodes")
if apps is not None:
    print("\n已安装 app:")
    for a in apps:
        mark = " <<<" if "google" in (a["title"] + a["handle"]).lower() else ""
        print(f"  {a['title']:<40} {a['handle']}{mark}")
else:
    print("\n(apps 查询无权限, 跳过 —", str(r2.get("errors", ""))[:120], ")")

# 3) 抽样 Google 渠道里的产品发布状态
r3 = gql("""{ publications(first: 20) {
  nodes { name products(first: 5, query: "zebra") {
    nodes { title onlineStoreUrl } } } } }""")
for n in r3.get("data", {}).get("publications", {}).get("nodes", []):
    if "google" in n["name"].lower():
        print("\nGoogle 渠道 zebra 抽样:")
        for p in n["products"]["nodes"]:
            print("  -", p["title"][:60])
        if not n["products"]["nodes"]:
            print("  (zebra 关键词无结果)")
