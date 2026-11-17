# -*- coding: utf-8 -*-
"""二分定位 422：改 logo_width / 加 logo 各试一次，打印完整错误体。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THEME_ID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
v = rest.request("GET", f"themes/{THEME_ID}/assets.json",
                 params={"asset[key]": "config/settings_data.json"})["asset"]["value"]
sd = json.loads(v)


def try_put(tag, mutate):
    d = json.loads(v)
    mutate(d["current"])
    payload = json.dumps(d, ensure_ascii=False, indent=2)
    try:
        rest.request("PUT", f"themes/{THEME_ID}/assets.json",
                     json_body={"asset": {"key": "config/settings_data.json", "value": payload}})
        print(tag, "OK")
        return True
    except Exception as e:
        attrs = {k: str(getattr(e, k, ""))[:500] for k in ("message", "payload", "details", "body", "args")}
        print(tag, "FAIL", attrs)
        return False


try_put("A only logo_width=150:", lambda c: c.update(logo_width=150))
try_put("B only logo=logo-estry.png:", lambda c: c.update(logo="logo-estry.png"))
