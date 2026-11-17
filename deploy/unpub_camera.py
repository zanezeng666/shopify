# -*- coding: utf-8 -*-
"""camera-battery collection unpublish（0 ACTIVE，用户明示不做 Camera）。"""
import sys

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
creds = cl.creds
headers = {"Accept": "application/json", "Content-Type": "application/json"}
if getattr(cl, "_token", None):
    headers["X-Shopify-Access-Token"] = cl._token
hc = httpx.Client(base_url=f"https://{creds.domain}/admin/api/2025-01/",
                  timeout=60, headers=headers, auth=cl._auth)

uq = """mutation collectionUnpublish($input: CollectionUnpublishInput!) {
  collectionUnpublish(input: $input) {
    collection { id handle }
    userErrors { field message }
  }
}"""
r = hc.post("graphql.json", json={"query": uq, "variables": {"input": {
    "id": "gid://shopify/Collection/159760351332",
    "collectionPublications": [
        {"publicationId": "gid://shopify/Publication/13882720356"}]}}})
print(r.json()["data"]["collectionUnpublish"])
