"""回读样例产品定义句 + 批量抽检 22 个产品定义句覆盖率。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
c = rest.client

# 1) 样例产品定义句原文
b = c.request("GET", "products/15476051902708.json",
              params={"fields": "body_html"})["product"]["body_html"]
m = re.search(r"This is a [^.]*\.", b)
print("sample sentence:", m.group(0) if m else "MISSING")

# 2) 全量覆盖统计（分页拉 body_html）
pid = None
total = hit = 0
while True:
    params = {"limit": 50, "fields": "id,body_html", "status": "draft"}
    if pid:
        params["since_id"] = pid
    items = c.request("GET", "products.json", params=params).get("products", [])
    if not items:
        break
    for p in items:
        total += 1
        if "This is a" in p["body_html"]:
            hit += 1
    pid = items[-1]["id"]
    if len(items) < 50:
        break
print(f"coverage: {hit}/{total}")
