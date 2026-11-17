"""只读：店铺已安装主题清单（角色/名称/创建时间）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

ts = ShopifyRest(StoreService().get_client(1)).client.request("GET", "themes.json")["themes"]
for t in ts:
    print(t["id"], "|", t["role"], "|", t["name"], "|", t.get("created_at", "")[:10])
