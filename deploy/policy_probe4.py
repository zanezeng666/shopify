# -*- coding: utf-8 -*-
"""introspect shopPolicyUpdate 完整签名。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
q = ('{ __type(name: "ShopPolicyInput") { inputFields { name type { name kind '
     'ofType { name kind } } } } }')
g = c.graphql(q)
print(json.dumps(g, ensure_ascii=False))
