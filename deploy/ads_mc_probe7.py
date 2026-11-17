# -*- coding: utf-8 -*-
"""merchantapi 商品列表探针（MC=136469408）：端点活性+返回结构+总量。"""
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
    f"https://merchantapi.googleapis.com/products/v1beta/accounts/{MC}/products",
    params={"pageSize": 5}, headers=HDR, timeout=30)
print(f"HTTP {r.status_code}")
if r.status_code != 200:
    print(r.text[:400])
    raise SystemExit(1)

b = r.json()
prods = b.get("products", [])
print(f"首页 {len(prods)} 个，nextPageToken={'有' if b.get('nextPageToken') else '无'}")
for p in prods[:5]:
    attrs = p.get("attributes", {})
    print(f"  name={p.get('name', '')[:78]}")
    print(f"    channel={p.get('channel')} offerId={p.get('offerId', '')[:44]}")
    print(f"    title={str(attrs.get('title', ''))[:56]}")
    print(f"    productType={attrs.get('productTypes', '')} "
          f"link={str(attrs.get('link', ''))[:60]}")

# 总量（走第二页 token 快速统计上限 5 页）
tok = b.get("nextPageToken")
total = len(prods)
pages = 1
while tok and pages < 5:
    r2 = httpx.get(
        f"https://merchantapi.googleapis.com/products/v1beta/accounts/"
        f"{MC}/products",
        params={"pageSize": 250, "pageToken": tok}, headers=HDR, timeout=60)
    if r2.status_code != 200:
        print(f"翻页失败 HTTP {r2.status_code}: {r2.text[:150]}")
        break
    b2 = r2.json()
    total += len(b2.get("products", []))
    tok = b2.get("nextPageToken")
    pages += 1
print(f"\n前 {pages} 页共 {total} 个商品（pageSize=250）"
      f"{'（还有更多页）' if tok else '（已到末页）'}")
