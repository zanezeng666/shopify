# -*- coding: utf-8 -*-
"""MC API 访问实测：token scope 列表 + PMax 系列绑定的 MC ID
+ Content API / merchantapi 商品列表探针。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

# ---- 1. refresh_token 换 access_token，看 scope ----
tr = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()
at = tr["access_token"]
print("=== token 授权 scope ===")
print(f"  {tr.get('scope')}")

# ---- 2. PMax 系列绑定的 MC ID ----
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
MC = None
try:
    for r in gas.search(customer_id=CID, query=(
            "SELECT campaign.shopping_setting.merchant_center_id, "
            "campaign.shopping_setting.feed_label "
            f"FROM campaign WHERE campaign.id = {PMAX}")):
        ss = r.campaign.shopping_setting
        MC = ss.merchant_center_id
        print(f"\n=== PMax 绑定 MC ===\n  MC ID={MC} feed_label={ss.feed_label!r}")
except Exception as e:  # noqa
    print(f"\nshopping_setting 查询失败: {str(e)[:200]}")

if not MC:
    raise SystemExit("拿不到 MC ID，终止")

HDR = {"Authorization": f"Bearer {at}"}

# ---- 3a. Content API v2.1 探针 ----
print("\n=== Content API v2.1 products list 探针 ===")
r = httpx.get(
    f"https://shoppingcontent.googleapis.com/v2.1/{MC}/products",
    params={"maxResults": 3}, headers=HDR, timeout=30)
print(f"  HTTP {r.status_code}")
body = r.json() if r.headers.get("content-type", "").startswith(
    "application/json") else {}
for it in (body.get("resources") or [])[:3]:
    print(f"    {it.get('offerId', '?')[:60]} | "
          f"{str(it.get('title', ''))[:44]} | "
          f"tp={it.get('productType', '')[:36]}")
err = body.get("error", {})
if err:
    print(f"  error: {err.get('message', '')[:260]}")

# ---- 3b. merchantapi v1beta 探针 ----
print("\n=== merchantapi v1beta products list 探针 ===")
r2 = httpx.get(
    f"https://merchantapi.googleapis.com/products/v1beta/accounts/{MC}/products",
    params={"pageSize": 3}, headers=HDR, timeout=30)
print(f"  HTTP {r2.status_code}")
try:
    b2 = r2.json()
    for it in (b2.get("products") or [])[:3]:
        print(f"    {it.get('name', '?')[:70]} | "
              f"{str(it.get('title', ''))[:40]}")
    if b2.get("error"):
        print(f"  error: {b2['error'].get('message', '')[:260]}")
except Exception as e:  # noqa
    print(f"  解析失败: {e} | body={r2.text[:200]}")
