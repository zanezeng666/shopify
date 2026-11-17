# -*- coding: utf-8 -*-
"""确认 featured-collection heading 的真实 setting id。"""
import json
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
v = c.request("GET", "themes/190031036660/assets.json",
              params={"asset[key]": "sections/featured-collection.liquid"}
              )["asset"]["value"]
m = re.search(r"\{%-?\s*schema\s*-?%\}(.*?)\{%-?\s*endschema\s*-?%\}", v, re.S)
sch = json.loads(m.group(1))
print("settings ids:", [s.get("id") for s in sch.get("settings", [])])

idx = c.request("GET", "themes/190031036660/assets.json",
                params={"asset[key]": "templates/index.json"})["asset"]["value"]
fc = json.loads(idx)["sections"]["featured_collection"]
print("featured_collection.settings keys:", list(fc.get("settings", {}).keys()))
print("heading value:", fc.get("settings", {}).get("heading"))
