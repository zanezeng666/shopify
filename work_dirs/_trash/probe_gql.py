# -*- coding: utf-8 -*-
"""探测 fileCreate 完整响应形状。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402

client = StoreService().get_client(1)
rest = None
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
rest = ShopifyRest(client).client
pub = rest.request("GET", "themes/190031036660/assets.json",
                   params={"asset[key]": "assets/logo-estry.png"})["asset"].get("public_url")
print("pub:", pub)

MUT = """
mutation FileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files { id fileStatus }
    userErrors { field message }
  }
}
"""
r = client.graphql(MUT, {"files": [{"originalSource": pub, "contentType": "IMAGE"}]})
print("FULL:", json.dumps(r, ensure_ascii=False)[:800])
