# -*- coding: utf-8 -*-
"""P0-2b MC 权限复核 v3：GAQL 直查 merchant_id（避开废弃的 sales_country）"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {TOK}", "developer-token": "unused",
     "login-customer-id": CID}

r = httpx.post(
    f"https://googleads.googleapis.com/v25/customers/{CID}/googleAds:searchStream",
    headers=H, json={"query": """
        SELECT campaign.name, campaign.shopping_setting.merchant_id,
          campaign.shopping_setting.feed_label
        FROM campaign
        WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX'
          AND campaign.status != 'REMOVED'"""}, timeout=60)
if r.status_code != 200:
    print("GAQL err:", r.text[:500])
    raise SystemExit
mids = set()
for batch in r.json():
    for row in batch.get("results", []):
        ss = row["campaign"].get("shoppingSetting") or {}
        mids.add(ss.get("merchantId"))
        print("PMax:", row["campaign"]["name"], "merchant:",
              ss.get("merchantId"), "feed:", ss.get("feedLabel"))

if not mids:
    print("未找到 merchant_id")
    raise SystemExit
mid = str(list(mids)[0])
print(f"\n实测 Content API (merchant {mid}) ...")
r = httpx.get(
    f"https://shoppingcontent.googleapis.com/content/v2.1/{mid}/products",
    headers={"Authorization": f"Bearer {TOK}"}, timeout=60)
print("Content API status:", r.status_code)
print(r.text[:400] if r.status_code != 200
      else f"可访问！首屏商品数: {len(r.json().get('resources', []))}")
