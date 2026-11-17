# -*- coding: utf-8 -*-
"""拉 1 条完整 product JSON 看 attributes 真实键名+offer 形态统计。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MC = "136469408"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HDR = {"Authorization": f"Bearer {at}"}

r = httpx.get(
    f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}/products",
    params={"pageSize": 2}, headers=HDR, timeout=30)
print(f"HTTP {r.status_code}")
for p in r.json().get("products", []):
    print("=" * 60)
    print(f"name={p.get('name')}")
    print(f"offerId={p.get('offerId')}")
    print(f"顶级键: {sorted(p.keys())}")
    a = p.get("attributes", {})
    print(f"attributes 键: {sorted(a.keys())}")
    for k in ("title", "link", "productType", "productTypes", "productGroup",
              "googleProductCategory", "itemGroupId"):
        if k in a:
            print(f"  {k} = {str(a[k])[:70]}")
    for k in ("channel", "contentLanguage", "feedLabel", "versionNumber"):
        print(f"{k}={p.get(k)}")

# offer 前缀形态统计（拉 3 页）
tok = r.json().get("nextPageToken")
stats = {}
for _ in range(3):
    if not tok:
        break
    b = httpx.get(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"
        f"/products",
        params={"pageSize": 250, "pageToken": tok}, headers=HDR,
        timeout=60).json()
    for p in b.get("products", []):
        o = p.get("offerId", "")
        if o.startswith("shopify_"):
            stats["shopify_前缀"] = stats.get("shopify_前缀", 0) + 1
        elif o.isdigit() and len(o) <= 15:
            stats["纯数字<=15位"] = stats.get("纯数字<=15位", 0) + 1
        else:
            stats["其他"] = stats.get("其他", 0) + 1
    tok = b.get("nextPageToken")
print(f"\noffer 形态统计(3页样本): {stats}")
