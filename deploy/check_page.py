"""查 pages 发布状态，确认 contact-us 404 是否为未发布草稿页。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
for pg in c.request("GET", "pages.json", params={"limit": 10})["pages"]:
    print(pg["handle"], "| published_at:", pg.get("published_at"),
          "| title:", pg.get("title", "")[:40])
