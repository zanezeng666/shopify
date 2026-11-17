"""拉 battery-search 页面 body_html，存本地供分析。"""
import json
import pathlib
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

rest = ShopifyRest(StoreService().get_client(1)).client
pages = rest.request("GET", "pages.json", params={"limit": 250})["pages"]
target = next(p for p in pages if p["handle"] == "battery-search")
out = pathlib.Path("/tmp/bs_page.json")
out.write_text(json.dumps(target, ensure_ascii=False, indent=1), encoding="utf-8")
print("id", target["id"], "title", target["title"], "len", len(target["body_html"]))
print("saved", out)
