"""readback 验证 section 修复已落。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

rest = ShopifyRest(StoreService().get_client(1)).client
a = rest.request("GET", "themes/190031036660/assets.json",
                 params={"asset[key]": "sections/estry-battery-search.liquid"})["asset"]
v = a.get("value", "")
print("updated", a["updated_at"])
ok1 = "max-height:calc(100vh - 84px)" in v
ok2 = "position:sticky;top:0;background:#1B2A41" in v
ok3 = "background:transparent;max-height:none" in v
print("fix-inner-scroll", ok1, "fix-th-top0", ok2, "fix-mobile-reset", ok3)
print("RESULT", "PASS" if ok1 and ok2 and ok3 else "MISMATCH")
