# -*- coding: utf-8 -*-
"""打印 v22 listAccessibleCustomers 原始响应全文。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]

resp = httpx.get(
    "https://googleads.googleapis.com/v22/customers:"
    "listAccessibleCustomers",
    headers={"Authorization": f"Bearer {at}"}, timeout=20)
print("status:", resp.status_code)
print("headers:", {k: v for k, v in resp.headers.items()
                  if k.lower() in ("content-type", "www-authenticate")})
print("body:", resp.text[:1500])
