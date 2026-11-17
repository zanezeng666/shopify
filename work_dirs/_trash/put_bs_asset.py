"""上传修改后的 estry-battery-search section 资产。"""
import pathlib
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME = 190031036660
src = pathlib.Path("/tmp/estry-battery-search.liquid").read_text(encoding="utf-8")
for probe in ("max-height:calc(100vh - 84px)", "position:sticky;top:0", "max-height:none"):
    assert probe in src, f"missing: {probe}"

rest = ShopifyRest(StoreService().get_client(1)).client
r = rest.request("PUT", f"themes/{THEME}/assets.json",
                 json_body={"asset": {"key": "sections/estry-battery-search.liquid", "value": src}})
print("updated_at", r["asset"]["updated_at"], "size", r["asset"]["public_size"] or len(src))
