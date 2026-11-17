# -*- coding: utf-8 -*-
"""写回 footer.liquid。"""
import time
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
v = open("/tmp/footer_new.liquid", encoding="utf-8").read()
rest.request("PUT", f"themes/{TID}/assets.json", json_body={
    "asset": {"key": "sections/footer.liquid", "value": v}})
print("PUT ok", len(v))
time.sleep(30)
back = rest.request("GET", f"themes/{TID}/assets.json",
                    params={"asset[key]": "sections/footer.liquid"})["asset"]["value"]
print("about-link", "/pages/about" in back, "faq-link", "/pages/faq" in back, "identical", back == v)
