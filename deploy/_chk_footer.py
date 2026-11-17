# -*- coding: utf-8 -*-
"""检查 footer.liquid 是否已注入 + 前后文."""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
f = c.request("GET", "themes/190031036660/assets.json",
              params={"asset[key]": "sections/footer.liquid"})["asset"]["value"]
f = f.replace("\r\n", "\n")
print("has-mark:", "estry-b2b-links-v1" in f)
print("len:", len(f))
i = f.find("footer__content-bottom-wrapper")
print("anchor-pos:", i)
if i >= 0:
    print("ctx:", repr(f[i - 60:i + 320]))
