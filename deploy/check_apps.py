"""查店铺已安装 app（找 Google channel）+ 订单访问会话线索。只读。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
apps = c.request("GET", "apps.json")["apps"]
print(f"已安装 app {len(apps)} 个：")
for a in apps:
    print(f"  [{a['id']}] {a['name']}  (installed: {a.get('created_at','?')[:10]})")
