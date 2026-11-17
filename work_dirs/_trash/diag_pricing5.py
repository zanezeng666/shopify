# -*- coding: utf-8 -*-
"""判定：REST 404（真删）还是 SKU 仍在远端（pid 错位）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

rest = ShopifyRest(StoreService().get_client(1)).client

for pid, sku in [(4616097661028, "CS-MKM180PW_Milwaukee_55_0"),
                 (4626128666724, "CS-BP1100_Kyocera_9_0")]:
    try:
        p = rest.request("GET", f"products/{pid}.json")
        print(pid, "REST EXISTS:", p["product"]["status"], p["product"]["handle"])
    except Exception as e:
        print(pid, "REST:", str(getattr(e, "code", e))[:60])

# SKU 搜索（REST 变体 SKU 查询）
try:
    r = rest.request("GET", "products.json",
                     params={"limit": 5, "handle": "cs-mkm180pw-milwaukee-55"})
    print("handle search:", [(p["id"], p["status"]) for p in r.get("products", [])] or "NONE")
except Exception as e:
    print("handle err:", str(e)[:100])
try:
    r2 = rest.request("GET", "variants/search.json",
                      params={"query": "sku:CS-MKM180PW_Milwaukee_55_0", "limit": 3})
    print("sku search:", [(v.get("id"), v.get("sku"), v.get("product_id")) for v in r2.get("variants", [])] or "NONE")
except Exception as e:
    print("sku err:", str(e)[:100])
