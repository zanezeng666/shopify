# -*- coding: utf-8 -*-
"""删源后全量复核：总数 + 按数据源分布。"""
import os
import time
from collections import Counter

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

cnt, tok, total, t0 = Counter(), None, 0, time.time()
while True:
    params = {"pageSize": 250}
    if tok:
        params["pageToken"] = tok
    b = httpx.get(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"
        f"/products", params=params, headers=HD, timeout=60).json()
    for p in b.get("products", []):
        cnt[(p.get("dataSource") or "").rsplit("/", 1)[-1]] += 1
        total += 1
    tok = b.get("nextPageToken")
    if not tok:
        break
    time.sleep(0.25)
print(f"MC 剩余商品总数: {total}（删源前 19,649）")
print(f"按数据源分布: {dict(cnt)}")
