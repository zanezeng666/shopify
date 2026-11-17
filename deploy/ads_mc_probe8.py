# -*- coding: utf-8 -*-
"""merchantapi products/v1 403 完整错误体定位。"""
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
print(r.text[:1500])
