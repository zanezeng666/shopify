# -*- coding: utf-8 -*-
"""Merchant API 端点探测 v2：服务分模块 host"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

probes = [
    ("merchant/products/v1",
     f"https://merchantapi.googleapis.com/products/v1/accounts/{MID}/products?pageSize=2"),
    ("merchant/products/v1beta",
     f"https://merchantapi.googleapis.com/products/v1beta/accounts/{MID}/products?pageSize=2"),
    ("content/v2.1 products(残留)",
     f"https://shoppingcontent.googleapis.com/content/v2.1/{MID}/products?maxResults=2"),
]
for tag, url in probes:
    try:
        r = httpx.get(url, headers=H, timeout=60)
        body = r.text[:600].replace("\n", " ")
        print(f"[{r.status_code}] {tag}\n    {body}\n")
    except Exception as e:
        print(f"[ERR] {tag}: {e}\n")
