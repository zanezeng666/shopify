"""线上回读：Tips 段已移除、FAQ 折叠完好。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

b = ShopifyRest(StoreService().get_client(1)).client.request(
    "GET", "products/15476051902708.json",
    params={"fields": "body_html"})["product"]["body_html"]
print("Tips gone:", "Tips Before Purchase" not in b)
print("FAQ intact:", "<details" in b, "| confirm-fit FAQ:", "confirm this battery fits" in b)
print("bytes:", len(b))
