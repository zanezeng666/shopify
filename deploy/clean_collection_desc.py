# -*- coding: utf-8 -*-
"""清除 16 个 collection 的污染 body_html（CS 类目清单+垃圾占位句）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

BAD_KEYS = ("data-v-", "Magnifier", "Thermal Electric", "Toothbrush",
            "Microscope", "Personal Care", "We sold all kinds")

done = []
for ep, key in (("smart_collections.json", "smart_collections"),
                ("custom_collections.json", "custom_collections")):
    cols = cl.request("GET", ep, params={"limit": 250}).get(key, [])
    for c in cols:
        bh = c.get("body_html") or ""
        if not any(k in bh for k in BAD_KEYS):
            continue
        upd_ep = ep.replace(".json", f"/{c['id']}.json")
        cl.request("PUT", upd_ep, json_body={
            key.rstrip("s"): {"id": c["id"], "body_html": ""}})
        # 回读验证
        back = cl.request("GET", upd_ep).get(key.rstrip("s"), {})
        ok = not (back.get("body_html") or "").strip()
        done.append((c["handle"], ok))
        print(f"{'OK ' if ok else 'FAIL'} {c['handle']}")

print(f"\n清理 {sum(1 for _, o in done if o)}/{len(done)}")
