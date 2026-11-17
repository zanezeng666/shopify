# -*- coding: utf-8 -*-
"""多候选连测 settings.logo 写入：裸名 / hash 名（重试+回读原始键）。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
client = StoreService().get_client(1)
rest = ShopifyRest(client).client

CANDS = [
    "shopify://shop_images/logo-estry.png",
    "shopify://shop_images/logo-estry_e177aa14-76aa-4d73-819e-d831da3afbac.png",
]


def readback():
    v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                     params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
    c = json.loads(v).get("current", {})
    return {k: c[k] for k in c if "logo" in k.lower()}, v


for c in CANDS:
    v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                     params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
    sd = json.loads(v)
    sd["current"]["logo"] = c
    sd["current"]["logo_width"] = 150
    try:
        rest.request("PUT", f"themes/{THEME_ID}/assets.json",
                     json_body={"asset": {"key": "config/settings_data.json",
                                          "value": json.dumps(sd, ensure_ascii=False, indent=2)}})
    except Exception as e:
        print("PUT rejected:", c[:60], str(getattr(e, "details", ""))[:200])
        continue
    keys, _ = readback()
    print("PUT ok:", c[:70], "-> readback logo keys:", keys)
    if keys.get("logo"):
        print("PASS")
        sys.exit(0)

print("ALL FAILED")
sys.exit(1)
