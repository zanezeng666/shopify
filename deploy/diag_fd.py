"""诊断：main-product.liquid 现状 + assets PUT 真实响应行为。只读为主。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

TID = 190031036660
c = ShopifyRest(StoreService().get_client(1)).client

r = c.request("GET", f"themes/{TID}/assets.json", params={"asset[key]": "sections/main-product.liquid"})
a = r["asset"]
v = a.get("value", "") or ""
print("bytes:", len(v), "| updated_at:", a.get("updated_at"))
print("fd-note:", "fd-note" in v, "| factory_direct:", "factory_direct" in v)

# when 'price' 上下文（看是否已插入）
i = v.find("when 'price'")
print("--- when price 之后 300 字符 ---")
print(v[i:i + 300])

# 测 PUT 行为：写一个无害小资产并观察响应结构
resp = c.request("PUT", f"themes/{TID}/assets.json",
                 json_body={"asset": {"key": "templates/product.factory-direct-probe.json", "value": "{}"}})
print("PUT probe resp keys:", type(resp), str(resp)[:200])
