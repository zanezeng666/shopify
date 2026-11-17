# -*- coding: utf-8 -*-
"""精确复验: 逐变体单查 inventory_levels 求和, 杜绝批量漏行误报。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,variants", "status": "active"}
allp = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>")
           for x in link.split(",") if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

multi = [p for p in allp if len(p.get("variants") or []) > 1]
print(f"多变体品 {len(multi)}")

sold = []
nvar = 0
for p in multi:
    for v in p["variants"]:
        iid = v.get("inventory_item_id")
        if not iid:
            continue
        nvar += 1
        r = cl._client.get("inventory_levels.json",
                           params={"inventory_item_ids": iid}, auth=cl._auth)
        rows = r.json().get("inventory_levels", [])
        total = sum(x["available"] for x in rows)
        if total <= 0:
            sold.append((p["handle"], v.get("option1"),
                         v.get("sku"), iid, len(rows)))
        time.sleep(0.15)

print(f"变体总数 {nvar}, 真 soldout {len(sold)}")
for h, o1, sku, iid, nr in sold[:20]:
    print(f"SOLD {h[:44]:<44} {o1:>9} {sku} rows={nr}")
if len(sold) > 20:
    print(f"... 其余 {len(sold) - 20} 个")
