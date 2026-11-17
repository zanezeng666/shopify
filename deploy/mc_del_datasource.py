# -*- coding: utf-8 -*-
"""删除废弃 AUTOFEED 旧源 10604168290（7,600 死链的唯一来源）。"""
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MC = "136469408"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HD = {"Authorization": f"Bearer {at}"}

url = (f"https://merchantapi.googleapis.com/datasources/v1/accounts/{MC}"
       f"/dataSources/10604168290")
r = httpx.delete(url, headers=HD, timeout=60)
print(f"删除数据源 → HTTP {r.status_code}")
print(r.text[:300])

print("\n等待 90s 后复核商品数...")
time.sleep(90)
r2 = httpx.get(
    f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"
    f"/products", params={"pageSize": 250}, headers=HD, timeout=60)
b = r2.json()
total = len(b.get("products", []))
tok = b.get("nextPageToken")
pages = 1
while tok and pages < 5:  # 抽 5 页估趋势
    bb = httpx.get(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"
        f"/products", params={"pageSize": 250, "pageToken": tok},
        headers=HD, timeout=60).json()
    total += len(bb.get("products", []))
    tok = bb.get("nextPageToken")
    pages += 1
print(f"前 {pages} 页商品数: {total}（删源前同口径约 {pages * 250}）")
old_left = sum(1 for _ in ())
