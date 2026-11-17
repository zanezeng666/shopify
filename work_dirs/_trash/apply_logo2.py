# -*- coding: utf-8 -*-
"""logo 引用修正：取 assets public_url 填入 settings.logo（Dawn 要求 valid shopify url）。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client

img = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                   params={"asset[key]": "assets/logo-estry.png"})["asset"]
pub = img.get("public_url")
print("public_url:", pub)
if not pub:
    sys.exit("no public_url")

v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                 params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
sd = json.loads(v)
sd["current"]["logo"] = pub
sd["current"]["logo_width"] = 150
try:
    rest.request("PUT", f"themes/{THEME_ID}/assets.json",
                 json_body={"asset": {"key": "config/settings_data.json",
                                      "value": json.dumps(sd, ensure_ascii=False, indent=2)}})
    print("PUT OK")
except Exception as e:
    print("PUT FAIL:", str(getattr(e, "details", ""))[:300])
    sys.exit(1)

back = json.loads(rest.request("GET", f"themes/{THEME_ID}/assets.json",
                               params={"asset[key]": "config/settings_data.json"})["asset"]["value"])
c = back["current"]
print("readback logo:", c.get("logo", "")[:80])
print("readback width:", c.get("logo_width"))
print("PASS" if c.get("logo") == pub and c.get("logo_width") == 150 else "MISMATCH")
