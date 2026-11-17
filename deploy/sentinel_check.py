# -*- coding: utf-8 -*-
"""哨兵抽验: zebra(看老系统是否adjust) + worx/zondan(看fix是否保留)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,variants", "status": "active"}
targets = {}
want = ("battery-for-zebra-zr138", "battery-for-worx-landroid-s300",
        "battery-for-zondan-apollo-n3")
while len(targets) < len(want):
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    for x in r.json()["products"]:
        for w in want:
            if w in x["handle"] and w not in targets:
                targets[w] = x
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

for w, p in targets.items():
    print(f"== {w}")
    for v in p["variants"]:
        iid = v.get("inventory_item_id")
        if not iid:
            continue
        r = cl._client.get("inventory_levels.json",
                           params={"inventory_item_ids": iid}, auth=cl._auth)
        rows = r.json().get("inventory_levels", [])
        det = " ".join(f"L{x['location_id'] % 10000}:{x['available']}"
                       for x in rows)
        print(f"  {v['option1']:>8} {v.get('sku', '')[:30]:<30} "
              f"合计={sum(x['available'] for x in rows):>4} [{det}]")
