# -*- coding: utf-8 -*-
"""试点验证：变体结构 + 线上渲染 + 301。"""
import re
import sys
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

CHECKS = [
    # (主品id, 主品handle, 被删handle样例)
    (15485325312244, "battery-for-sichler-reinigungs-roboter-pcr-1350-l-pcr-2350-lx-nc-3337-nc-3338-pcr-3350",
     "battery-for-vileda-488a-a3"),
    (15484830548212, None, None),  # 组1主品 handle 长截断，单独查
]

# 1) 组1 主品变体结构（DeWalt 组顺带）
for pid in (15485325312244, 15484830548212):
    p = cl.request("GET", f"products/{pid}.json",
                   params={"fields": "handle,title,variants"}).get("product", {})
    print(f"\n== {p['handle'][:60]}")
    for v in p["variants"]:
        print(f"   {v['option1']:<10} ${v['price']:<8} sku={v['sku']}")

# 2) 线上渲染：变体选择器 + 价格区间
h = "battery-for-sichler-reinigungs-roboter-pcr-1350-l-pcr-2350-lx-nc-3337-nc-3338-pcr-3350"
req = urllib.request.Request(f"https://estrybattery.com/products/{h}",
                             headers={"User-Agent": "Mozilla/5.0"})
html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
print("\n线上页面:")
print("  容量选项值:", sorted(set(re.findall(r'value="(1|2|3|\d{3,5}mAh)"', html)))[:8])
print("  变体 JSON 注入:", "variants" in html and bool(
    re.search(r'"\d{3,5}mAh"', html)))
m = re.search(r'price":\s*"([\d.]+)".*?"priceMin', html)
mm = re.findall(r'"price":\s*"?([\d.]+)"?', html)[:6]
print("  价格字段样例:", mm)

# 3) redirect 生效（被删 handle 应 301 到主品）
test_old = "battery-for-vileda-488a-a3"
req2 = urllib.request.Request(f"https://estrybattery.com/products/{test_old}",
                              headers={"User-Agent": "Mozilla/5.0"})
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None
op = urllib.request.build_opener(NoRedirect)
try:
    op.open(req2, timeout=20)
    print(f"\n301 测试 {test_old}: 未重定向(!)")
except urllib.error.HTTPError as e:
    print(f"\n301 测试 {test_old}: HTTP {e.code} -> {e.headers.get('Location', '')[:70]}")
