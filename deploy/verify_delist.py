# -*- coding: utf-8 -*-
"""抽验下架生效。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

client = ShopifyRest(StoreService().get_client(1)).client
for h in ("battery-for-toshiba-vc-j1x-th-4-3apt-16",
          "battery-for-htc-doubleshot-mytouch-4g-slide-pg59100-35h00150-00m-35h00150-01m-35h00150-02m-35h00150-06m-ba-s560-bg58100"):
    r = client.graphql(
        '{ productByHandle(handle: "%s") { status handle } }' % h)
    print(r["productByHandle"])
