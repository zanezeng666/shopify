import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
cases = {
    "limit_only": {"limit": 5},
    "limit_page": {"limit": 5, "page": 1},
    "limit_min": {"limit": 5, "created_at_min": "2026-10-30T00:00:00Z"},
    "limit_fields": {"limit": 5, "fields": "id,handle,body_html,created_at,variants"},
}
for name, params in cases.items():
    try:
        r = rest.client.request("GET", "products.json", params=params)
        print(name, "OK n=", len(r.get("products", [])))
    except Exception as e:
        print(name, "FAIL", str(e)[:200])
