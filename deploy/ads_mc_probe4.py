# -*- coding: utf-8 -*-
"""从 Ads 侧拿 MC ID：GAQL 单字段 + REST GET campaign 兜底
+ merchantapi 按已知 MC 试商品第一页。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

# ---- 1. GAQL 单字段 ----
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
MC = None
for q in (
    "SELECT campaign.shopping_setting.merchant_center_id "
    f"FROM campaign WHERE campaign.id = {PMAX}",
    "SELECT campaign.shopping_setting.merchant_center_id, "
    "campaign.shopping_setting.sales_country, "
    "campaign.shopping_setting.campaign_priority "
    f"FROM campaign WHERE campaign.id = {PMAX}",
):
    try:
        for r in gas.search(customer_id=CID, query=q):
            ss = r.campaign.shopping_setting
            MC = ss.merchant_center_id
            print(f"GAQL: MC ID={MC} sales_country={ss.sales_country!r}")
        if MC:
            break
    except Exception as e:  # noqa
        errs = [ln.strip() for ln in str(e).split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"GAQL FAIL {errs[:1]}")

# ---- 2. REST GET campaign 兜底 ----
if not MC:
    at = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
    r = httpx.get(
        f"https://googleads.googleapis.com/v26/customers/{CID}/campaigns/"
        f"{PMAX}", headers={"Authorization": f"Bearer {at}",
                            "developer-token": "unused"}, timeout=30)
    print(f"REST campaign: HTTP {r.status_code}")
    try:
        c = r.json()
        ss = c.get("shoppingSetting", {})
        MC = ss.get("merchantCenterId")
        print(f"  shoppingSetting={ss}")
    except Exception as e:  # noqa
        print(f"  {e} | {r.text[:200]}")

if not MC:
    raise SystemExit("拿不到 MC ID")
print(f"\n最终 MC ID = {MC}")

# ---- 3. merchantapi 商品第一页（用 Ads token 不行，用 MC token）----
at2 = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HDR = {"Authorization": f"Bearer {at2}"}

for url in (
    f"https://merchantapi.googleapis.com/products/v1beta/accounts/{MC}"
    "/products?pageSize=3",
    f"https://shoppingcontent.googleapis.com/v2.1/{MC}/products"
    "?maxResults=3",
):
    r = httpx.get(url, headers=HDR, timeout=30)
    print(f"\nGET {url.split('googleapis.com')[1][:60]} → HTTP {r.status_code}")
    if r.status_code == 200:
        b = r.json()
        prods = b.get("products") or b.get("resources") or []
        for p in prods[:3]:
            print(f"  {str(p.get('name', p.get('offerId')))[:70]}")
            print(f"    title={str(p.get('title', ''))[:50]}")
            attrs = p.get("attributes") or {}
            print(f"    productType={attrs.get('productTypes') or p.get('productType', '')}")
        break
    print(f"  {r.text[:220]}")
