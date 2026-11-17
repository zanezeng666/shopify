# -*- coding: utf-8 -*-
"""探针10: 扫全部 Delivery* 类型, 找 methodDefinition 输入链的挂载点."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client

r = c.graphql("{ __schema { types { name kind } } }")
names = sorted(t["name"] for t in r["__schema"]["types"]
               if t["name"] and "Delivery" in t["name"])
print("Delivery* 类型:")
for n in names:
    print(" ", n)
