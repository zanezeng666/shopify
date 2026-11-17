# -*- coding: utf-8 -*-
"""验证8个补图产品的图片数与状态。只读。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client
PIDS = ["7124630208679", "7124606877863", "7122491900071", "7124630700199",
        "7122307940519", "7124628832423", "7122488361127", "7122493702311"]
ok = 0
for pid in PIDS:
    p = cl.request("GET", f"products/{pid}.json",
                   params={"fields": "id,status,images"})
    pd = p["product"]
    n = len(pd["images"])
    ok += (pd["status"] == "active" and n >= 1)
    print(f"{pid}: status={pd['status']} images={n}")
print(f"\n合格(active且有图): {ok}/8")
