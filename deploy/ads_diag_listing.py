# -*- coding: utf-8 -*-
"""PMax listing_group（商品组树）现状 + 线上存活商品抽样健康。"""
import os
import time

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

print("=== PMax listing_group_filter（商品组树）===")
q = (
    "SELECT asset_group_listing_group_filter.resource_name, "
    "asset_group_listing_group_filter.asset_group, "
    "asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_category.category_id, "
    "asset_group_listing_group_filter.case_value.brand.value, "
    "asset_group_listing_group_filter.parent_listing_group_id, "
    "asset_group_listing_group_filter.type_ "
    f"FROM asset_group_listing_group_filter WHERE campaign.id = {PMAX}"
)
try:
    rs = list(gas.search(customer_id=CID, query=q))
    if not rs:
        print("  (无 listing_group_filter = ALL_PRODUCTS 全商品投放)")
    for r in rs:
        f = r.asset_group_listing_group_filter
        cv = f.case_value
        desc = (f"type={f.type_.name} "
                f"ptype={cv.product_type.value or '-'} "
                f"brand={cv.brand.value or '-'} "
                f"parent={f.parent_listing_group_id}")
        print(f"  id={f.id} {desc}")
except Exception as e:  # noqa
    print(f"  查询失败: {e}")

print("\n=== 线上存活商品抽样（965 个 published 之 4 类各 2 个）===")
LIVE = [
    # 之前 Admin API 拉到 live 集合的样本 URL 手测：GPS/SmartPhone/Camera/Ebook
]
# 重拉每类 2 个（Admin API 快）
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
import sys  # noqa: E402

sys.path.insert(0, "/home/jason/shopify-admin/src")
cl = ShopifyRest(StoreService().get_client(1))
for pt in ("Camera Battery", "GPS, Navigator Battery",
           "Mobile, SmartPhone Battery", "E-book, E-reader Battery"):
    r = cl.client.request(
        "GET", "products.json",
        params={"limit": 2, "published_status": "published",
                "product_type": pt},
    )
    for p in r.get("products", []):
        LIVE.append((pt, p["handle"]))
        print(f"  样本 [{pt[:26]:26}] /products/{p['handle'][:60]}")

print("\n=== HTTP 抽测（3s 间隔防限流）===")
with httpx.Client(
    timeout=25, follow_redirects=True,
    headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
              "AppleWebKit/537.36 Chrome/120 Safari/537.36"},
) as hc:
    for pt, h in LIVE:
        u = f"https://www.estrybattery.com/products/{h}"
        try:
            r = hc.get(u)
            tl = r.text.lower()
            ok = (r.status_code == 200
                  and ("battery" in tl[:6000] or "estry" in tl[:6000]))
            print(f"  {r.status_code} {'OK' if ok else 'BAD'} [{pt[:20]:20}]"
                  f" /products/{h[:55]}")
        except Exception as e:  # noqa
            print(f"  ERR {type(e).__name__} {u[:80]}")
        time.sleep(3)
