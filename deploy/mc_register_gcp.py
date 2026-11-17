# -*- coding: utf-8 -*-
"""registerGcp：把 OAuth 凭证所属 GCP 项目(415310719420)注册到 MC 136469408。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]

r = httpx.post(
    "https://merchantapi.googleapis.com/accounts/v1/accounts/136469408/"
    "developerRegistration:registerGcp",
    headers={"Authorization": f"Bearer {at}",
             "Content-Type": "application/json"},
    json={}, timeout=30)
print(f"HTTP {r.status_code}")
print(r.text[:500])
