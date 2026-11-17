# -*- coding: utf-8 -*-
"""header 菜单绑定：estry-main-menu -> main-menu（新结构）。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
key = "sections/header-group.json"
a = cl.request("GET", "themes/190031036660/assets.json", params={"asset[key]": key})
grp = json.loads(a["asset"]["value"])
st = grp["sections"]["header"]["settings"]
print("原绑定:", st.get("menu"))
st["menu"] = "main-menu"
cl.request("PUT", "themes/190031036660/assets.json",
           json_body={"asset": {"key": key,
                                "value": json.dumps(grp, ensure_ascii=False)}})
a2 = cl.request("GET", "themes/190031036660/assets.json", params={"asset[key]": key})
st2 = json.loads(a2["asset"]["value"])["sections"]["header"]["settings"]
print("新绑定:", st2.get("menu"), "| 公告条仍为:",
      "12-Month" in a2["asset"]["value"])
