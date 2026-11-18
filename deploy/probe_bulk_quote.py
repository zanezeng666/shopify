"""侦察：main-product.liquid 里 Bulk Quote / View Full Specs 按钮的 HTML+CSS 上下文。只读。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
v = c.request("GET", "themes/190031036660/assets.json",
              params={"asset[key]": "sections/main-product.liquid"})["asset"]["value"]
open("/tmp/mp.liquid", "w").write(v)
print("bytes:", len(v))

# Bulk Quote / View Full Specs 出现位置
for pat in ("Bulk Quote", "View Full Specs", "bulk-quote", "specs-link", "wsi-md"):
    for m in re.finditer(re.escape(pat), v):
        i = m.start()
        print(f"\n===== '{pat}' @{i} =====")
        print(v[max(0, i - 700):i + 300])
        break  # 每个模式只打第一处（HTML 处）；样式另看

# 相关 class 的 CSS 定义块
for cls in ("bulk-quote", "specs", "btn", "quote-btn"):
    hits = [m.start() for m in re.finditer(cls, v)]
    print(f"\nclass '{cls}' hits: {len(hits)}")
