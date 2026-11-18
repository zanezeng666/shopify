"""订单 #2241 variant_id ↔ PMax 产品点击精确对号。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx
from google.ads.googleads.client import GoogleAdsClient

# ① Shopify 订单行项目
sys_path = "/home/jason/shopify-admin/src"
import sys
sys.path.insert(0, sys_path)
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
lst = c.request("GET", "orders.json?status=any&name=%232241&limit=5")["orders"]
o = next(x for x in lst if x.get("name") == "#2241")
pid, vid, sku = None, None, None
for li in o["line_items"]:
    pid, vid, sku = li.get("product_id"), li.get("variant_id"), li.get("sku")
    print(f"订单行: {li['title'][:40]} | product_id={pid} variant_id={vid} sku={sku}")
item = f"shopify_us_{pid}_{vid}"

# ② Ads 侧全量产品点击（11-15~18）grep 对号
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
r = gas.search(customer_id="7059800494", query=(
    "SELECT segments.product_item_id, segments.date, metrics.clicks, metrics.impressions, "
    "metrics.cost_micros FROM shopping_performance_view "
    "WHERE segments.date BETWEEN '2026-11-15' AND '2026-11-18' LIMIT 10000"))
print(f"\n在 PMax 产品清单中查找 {item}（sku={sku}）：")
hit = False
for row in r:
    if row.segments.product_item_id == item:
        hit = True
        print(f"  ★ {row.segments.date} | {row.metrics.clicks}clk {row.metrics.impressions}imp "
              f"{row.metrics.cost_micros/1e6:.2f}CNY")
if not hit:
    print("  无直接命中；该视图只含购物分量，PMax 文本/展示分量点击不在此列")
