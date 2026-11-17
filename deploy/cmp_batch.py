# -*- coding: utf-8 -*-
"""对照: 同两个 iid 单查 vs 批量查。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
IIDS = ["70032049701108", "70027472175348"]

for iid in IIDS:
    r = cl._client.get("inventory_levels.json",
                       params={"inventory_item_ids": iid}, auth=cl._auth)
    print("单查", iid, [(x["location_id"], x["available"])
                       for x in r.json().get("inventory_levels", [])])

r = cl._client.get("inventory_levels.json",
                   params={"inventory_item_ids": ",".join(IIDS)},
                   auth=cl._auth)
print("批量", [(x["inventory_item_id"], x["location_id"], x["available"])
              for x in r.json().get("inventory_levels", [])])
