# -*- coding: utf-8 -*-
"""拉 footer.liquid 看 bottom bar 结构。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TID = 190031036660
rest = ShopifyRest(StoreService().get_client(1)).client
a = rest.request("GET", f"themes/{TID}/assets.json",
                 params={"asset[key]": "sections/footer.liquid"})["asset"]
v = a["value"]
open("/tmp/footer.liquid", "w", encoding="utf-8").write(v)
print("bytes:", len(v))
for pat in [r"copyright", r"policies", r"payment", r"linklists", r"footer__"]:
    hits = [v[:m.start()].count("\n") + 1 for m in re.finditer(pat, v)][:8]
    print(pat, ":", hits)
