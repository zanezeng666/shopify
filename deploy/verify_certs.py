"""线上回读：验证 CE/RoHS/ISO9001 绝迹、UN38.3/MSDS 新口径生效。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
for pid in (15476051902708,):  # ihome 样例
    b = rest.client.request("GET", f"products/{pid}.json",
                            params={"fields": "body_html"})["product"]["body_html"]
    print(f"--- product {pid} ---")
    print("CE:", "CE" in b, "| RoHS:", "RoHS" in b)
    print("UN38.3 badge:", "UN38.3 &amp; ISO9001 Certified" in b)
    print("MSDS line:", "MSDS available upon request" in b,
          "| ISO9001 facility:", "ISO9001 certified facility" in b)
    print("bytes:", len(b))
