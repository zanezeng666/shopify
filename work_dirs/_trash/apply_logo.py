# -*- coding: utf-8 -*-
"""换 Estry logo：上传 assets/logo-estry.png + settings_data.json 的 logo/logo_width。幂等。"""
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
LOGO_KEY = "assets/logo-estry.png"
LOGO_SRC = Path("/tmp/logo-estry.png")
LOGO_WIDTH = 150

rest = ShopifyRest(StoreService().get_client(1)).client


def put_asset(key, attachment_b64=None, value=None):
    asset = {"key": key}
    if attachment_b64:
        asset["attachment"] = attachment_b64
    if value is not None:
        asset["value"] = value
    rest.request("PUT", f"themes/{THEME_ID}/assets.json", json_body={"asset": asset})


# 1) 上传图片
b64 = base64.b64encode(LOGO_SRC.read_bytes()).decode()
put_asset(LOGO_KEY, attachment_b64=b64)
print("logo uploaded:", LOGO_KEY, LOGO_SRC.stat().st_size, "bytes")

# 2) 改 settings_data.json
cur = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                   params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
sd = json.loads(cur)
settings = sd.get("current", {})
old_logo = settings.get("logo")
settings["logo"] = "logo-estry.png"
settings["logo_width"] = LOGO_WIDTH
put_asset("config/settings_data.json", value=json.dumps(sd, ensure_ascii=False, indent=2))
print(f"settings logo: {old_logo!r} -> 'logo-estry.png', width={LOGO_WIDTH}")

# 3) 回读验证
back = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                    params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
chk = json.loads(back).get("current", {})
ok = chk.get("logo") == "logo-estry.png" and chk.get("logo_width") == LOGO_WIDTH
img = rest.request("GET", f"themes/{THEME_ID}/assets.json", params={"asset[key]": LOGO_KEY})["asset"]
print("readback settings:", "PASS" if ok else "MISMATCH", "| logo asset size:", img.get("size"))
