# -*- coding: utf-8 -*-
"""写回 estry-wholesale.liquid + main-product.liquid（询盘闭环版）。"""
import time
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client

for key, path, probes in [
    ("sections/estry-wholesale.liquid", "/tmp/sec_wholesale_new.liquid",
     ["generate_lead", "wsi-md"]),
    ("sections/main-product.liquid", "/tmp/main_product_new.liquid",
     ["quote_request", "#wsi-md"]),
]:
    v = open(path, encoding="utf-8").read()
    rest.request("PUT", f"themes/{TID}/assets.json", json_body={
        "asset": {"key": key, "value": v}})
    print("PUT", key, len(v))
    time.sleep(32)  # 传播时序 + 让批跑配额
    back = rest.request("GET", f"themes/{TID}/assets.json",
                        params={"asset[key]": key})["asset"]["value"]
    print(key, [(p, p in back) for p in probes], "identical", back == v)
