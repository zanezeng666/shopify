# -*- coding: utf-8 -*-
"""验证 body_html 真实内容 + 全店 collection 污染扫描。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

cols = []
for ep, key in (("smart_collections.json", "smart_collections"),
                ("custom_collections.json", "custom_collections")):
    cols += cl.request("GET", ep, params={"limit": 250}).get(key, [])

med = next(c for c in cols if c["handle"] == "medical-battery")
print("== Medical Battery body_html ==")
print(repr(med.get("body_html")))

print("\n== 全店 body_html 污染扫描 ==")
dirty = []
for c in cols:
    bh = c.get("body_html") or ""
    if any(k in bh for k in ("data-v-", "Magnifier", "Thermal Electric",
                             "Toothbrush", "Microscope", "Personal Care")):
        dirty.append((c["handle"], bh[:150]))
print(f"污染数: {len(dirty)}/{len(cols)}")
for h, bh in dirty:
    print(f"\n[{h}] {bh!r}")
