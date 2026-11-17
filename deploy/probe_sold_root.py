# -*- coding: utf-8 -*-
"""深查 soldout 根因: 变体跟踪状态/levels/sku。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

for pref in ("battery-for-black-decker-asd18-typ-1",
             "battery-for-zebra-rfd8500",
             "battery-for-proscenic-lds-m7-pro"):
    r = cl._client.get("products.json", params={
        "limit": 5, "handle": pref,
        "fields": "id,handle,variants"}, auth=cl._auth)
    ps = r.json().get("products", [])
    if not ps:
        r = cl._client.get("products.json", params={
            "limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
            "fields": "id,handle,variants", "status": "active"},
            auth=cl._auth)
        # 分页翻找
        ps = []
        while True:
            rr = r.json()["products"]
            ps += [p for p in rr if p["handle"].startswith(pref)]
            link = r.headers.get("Link", "")
            nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
                   if 'rel="next"' in x]
            if not nxt or ps:
                break
            r = cl._client.get(
                nxt[0].strip("<>").replace(
                    "https://bomibattery.myshopify.com/admin/api/2024-10/", ""),
                auth=cl._auth)
    for p in ps:
        print(f"== {p['handle'][:60]}")
        iids = []
        for v in sorted(p["variants"], key=lambda x: x["position"]):
            print(f"  {v['option1']:>9} sku={str(v.get('sku'))[:28]:<28} "
                  f"mgmt={v.get('inventory_management')} "
                  f"iid={v.get('inventory_item_id')}")
            if v.get("inventory_item_id"):
                iids.append(str(v["inventory_item_id"]))
        if iids:
            r = cl._client.get("inventory_levels.json",
                               params={"inventory_item_ids": ",".join(iids)},
                               auth=cl._auth)
            for x in r.json().get("inventory_levels", []):
                print(f"    loc={x['location_id']} avail={x['available']}")
        break
