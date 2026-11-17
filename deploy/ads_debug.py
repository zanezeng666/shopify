# -*- coding: utf-8 -*-
"""调试: 原始响应打印 campaign 查询。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]

q = ("SELECT campaign.id, campaign.name, campaign.status, "
     "campaign.advertising_channel_type, "
     "metrics.cost_micros, metrics.clicks, metrics.impressions "
     "FROM campaign WHERE campaign.status != 'REMOVED'")
r = httpx.post(
    "https://googleads.googleapis.com/v25/customers/7059800494/"
    "googleAds:searchStream",
    headers={"Authorization": f"Bearer {at}",
             "Content-Type": "application/json"},
    json={"query": q}, timeout=30)
print("status:", r.status_code)
print(r.text[:1500])
