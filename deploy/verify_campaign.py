# -*- coding: utf-8 -*-
"""验证 PMax Medical Estry 系列状态 + vendor 批改进度快查."""
import httpx
import json
import os
import pathlib

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"


def token():
    return httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


q = ("SELECT campaign.id, campaign.name, campaign.status, "
     "campaign.bidding_strategy_type, "
     "campaign.shopping_setting.merchant_id, "
     "campaign_budget.amount_micros "
     "FROM campaign WHERE campaign.id = 24441391608")
r = httpx.post(f"{API}/googleAds:searchStream",
               headers={"Content-Type": "application/json",
                        "developer-token": "unused",
                        "Authorization": f"Bearer {token()}"},
               json={"query": q}, timeout=60)
print("HTTP", r.status_code)
for arr in r.json():
    for row in arr.get("results", []):
        print(json.dumps(row, indent=1, ensure_ascii=False))
