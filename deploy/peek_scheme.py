# -*- coding: utf-8 -*-
import sys
import json

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
cur = json.loads(cl.request("GET", "themes/190031036660/assets.json",
                            params={"asset[key]": "config/settings_data.json"})["asset"]["value"])["current"]
s = cur.get("color_schemes", {})
for k, v in list(s.items())[:2]:
    st = v.get("settings", v)
    print(k, "->", json.dumps({kk: vv for kk, vv in st.items()
          if "button" in kk or kk in ("background", "text")}, ensure_ascii=False))
