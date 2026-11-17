"""拉 battery-search 模板链相关主题资产到 /tmp/bs_assets/。"""
import json
import pathlib
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
assets = rest.request("GET", f"themes/{THEME}/assets.json", params={"limit": 1000})["assets"]
keys = [a["key"] for a in assets if "battery-search" in a["key"] or "ebs" in a["key"].lower()
        or "estry" in a["key"].lower()]
out = pathlib.Path("/tmp/bs_assets")
out.mkdir(exist_ok=True)
for k in keys:
    item = rest.request("GET", f"themes/{THEME}/assets.json", params={"asset[key]": k})["asset"]
    (out / k.replace("/", "__")).write_text(item.get("value", ""), encoding="utf-8")
    print(k, len(item.get("value", "")))
print("DIR", out)
