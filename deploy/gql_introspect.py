# -*- coding: utf-8 -*-
"""内省 FileContentType 枚举值。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
r = cl._client.post(f"{cl._client.base_url}/graphql.json", auth=cl._auth,
                    json={"query": """
{a: __type(name: "FileContentType") {enumValues {name}}
 b: __type(name: "StagedUploadTargetGenerateUploadResource") {
   enumValues {name}}}"""}, timeout=30)
print(json.dumps(r.json(), ensure_ascii=False, indent=1)[:600])
