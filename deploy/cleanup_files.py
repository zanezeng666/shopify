# -*- coding: utf-8 -*-
"""清理 Shopify Files 里失败的 estry_feed 文件。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

def gql(query, variables=None):
    r = cl._client.post(f"{cl._client.base_url}/graphql.json",
                        auth=cl._auth,
                        json={"query": query, "variables": variables or {}},
                        timeout=30)
    return r.json()

q = gql("""{ files(first:20, sortKey: CREATED_AT, reverse: true) {
  nodes {id fileStatus ... on GenericFile {fileName}} } }""")
bad = [n["id"] for n in q["data"]["files"]["nodes"]
       if n["fileStatus"] == "FAILED"]
print("FAILED 文件:", bad)
if bad:
    d = gql("""mutation del($f: [ID!]!) { fileDelete(fileIds: $f) {
      deletedFileIds userErrors {field message} } }""", {"f": bad})
    print("删除结果:", json.dumps(d.get("data", d), ensure_ascii=False)[:200])
