# -*- coding: utf-8 -*-
"""GraphQL 拉 medical collection 成员，核对 product_type 与广告词对齐。"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

cl = ShopifyRest(StoreService().get_client(1))

Q = """
query($cursor: String) {
  collection(id: "gid://shopify/Collection/159760384100") {
    title
    products(first: 250, after: $cursor) {
      edges { node { title productType status } }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

prods = []
cursor = None
while True:
    r = cl.client.request(
        "POST", "graphql.json",
        json_body={"query": Q, "variables": {"cursor": cursor}},
    )
    coll = (r.get("data") or {}).get("collection")
    if not coll:
        print(f"collection 查询失败: {str(r)[:200]}")
        break
    for e in coll["products"]["edges"]:
        prods.append(e["node"])
    pi = coll["products"]["pageInfo"]
    if not pi["hasNextPage"]:
        break
    cursor = pi["endCursor"]

print(f"collection 成员: {len(prods)}")
ptc = Counter(p.get("productType") or "(空)" for p in prods)
print("productType 分布:", dict(ptc.most_common(6)))
stc = Counter(p.get("status") for p in prods)
print("status 分布:", dict(stc))

brands = ["welch allyn", "philips", "ge ", "mindray", "nihon", "fukuda",
          "fresenius", "alaris", "defib", "monitor", "ventilat", "ecg",
          "ultrasound", "zoll", "medtronic"]
tb = Counter()
for p in prods:
    t = p["title"].lower()
    for b in brands:
        if b in t:
            tb[b] += 1
            break
print("广告词覆盖:", dict(tb.most_common()))
print("\n抽样 title:")
for p in prods[:6]:
    print(f"  [{(p.get('productType') or '?')[:16]:16}] {p['title'][:66]}")
