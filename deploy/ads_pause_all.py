# -*- coding: utf-8 -*-
"""下架账号 7059800494 所有 ENABLED campaign (置 PAUSED, 可逆)。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID = "7059800494"
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}",
     "Content-Type": "application/json", "developer-token": "unused"}

TARGETS = [17176402315, 17557725557, 17652483274]
ops = [{"update": {"resourceName": f"customers/{CID}/campaigns/{t}",
                   "status": "PAUSED"},
        "updateMask": "status"} for t in TARGETS]
r = httpx.post(
    f"https://googleads.googleapis.com/v25/customers/{CID}/"
    "campaigns:mutate", headers=H,
    json={"operations": ops}, timeout=30)
print("mutate status:", r.status_code)
print(r.text[:600])

# 验证
q = ("SELECT campaign.id, campaign.status FROM campaign "
     "WHERE campaign.status = 'ENABLED'")
r2 = httpx.post(
    f"https://googleads.googleapis.com/v25/customers/{CID}/"
    "googleAds:searchStream", headers=H,
    json={"query": q}, timeout=30)
rows = r2.json() if isinstance(r2.json(), list) else [r2.json()]
left = sum(len(b.get("results", [])) for b in rows)
print("\n验证: ENABLED 剩余 =", left)
