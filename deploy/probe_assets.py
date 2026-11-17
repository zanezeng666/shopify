"""查看主题 2 资产中品牌字样的上下文行。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

THEME_ID = 136764817652
c = ShopifyRest(StoreService().get_client(1)).client
PAT = re.compile(r"bomibattery", re.I)

for key in ("config/settings_data.json", "sections/pf-837cba6e.liquid"):
    v = c.request("GET", f"themes/{THEME_ID}/assets.json",
                  params={"asset[key]": key})["asset"]["value"]
    print(f"===== {key} ({len(v)}B) =====")
    for i, ln in enumerate(v.splitlines(), 1):
        if PAT.search(ln):
            print(f"{i}: {ln.strip()[:240]}")
