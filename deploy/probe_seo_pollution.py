# -*- coding: utf-8 -*-
"""挖 Medical Battery 的 SEO listing metafield + 全店 collection 同类污染排查。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

# 1) Medical Battery 的 metafields
cols = []
for ep in ("smart_collections.json", "custom_collections.json"):
    cols += cl.request("GET", ep, params={"limit": 250}).get(ep.split(".")[0], [])
med = next(c for c in cols if c["handle"] == "medical-battery")
cid = med["id"]
print("== Medical Battery metafields ==")
mfs = cl.request("GET", f"collections/{cid}/metafields.json").get("metafields", [])
for m in mfs:
    print(f"  {m['namespace']}.{m['key']} = {str(m['value'])[:120]!r}")

# 2) collection 内产品 type 分布（GraphQL query 过滤）
hc = cl  # 同一 client，看它有没有 graphql 方法；rest 封装应有
# 用 REST collects 验证更直接：抽 collection 产品查 type
cids = cl.request("GET", f"collections/{cid}/products.json",
                  params={"limit": 250, "fields": "id,title,product_type"}).get("products", [])
types = {}
for p in cids:
    types[p["product_type"]] = types.get(p["product_type"], 0) + 1
print("\n== collection 前 250 产品 type 分布 ==", types)

# 3) 全店 collection SEO metafield 污染扫描
print("\n== 全店 collection SEO metafield 扫描 ==")
dirty = []
for c in cols:
    try:
        mlist = cl.request("GET", f"collections/{c['id']}/metafields.json").get("metafields", [])
    except Exception:
        continue
    for m in mlist:
        v = str(m.get("value") or "")
        if m.get("key") in ("description_tag", "description") and v and \
           any(k in v for k in ("Magnifier", "Thermal Electric", "Toothbrush", "Microscope")):
            dirty.append((c["handle"], m["namespace"], m["key"], v[:100]))
print(f"污染 collection 数: {len(dirty)}/{len(cols)}")
for d in dirty[:15]:
    print("  ", d)
