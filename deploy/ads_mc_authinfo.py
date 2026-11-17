# -*- coding: utf-8 -*-
"""Content API authinfo：授权用户可访问的 MC 账号清单。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HDR = {"Authorization": f"Bearer {at}"}

for url in (
    "https://shoppingcontent.googleapis.com/v2.1/accounts/authinfo",
    "https://content.googleapis.com/v2.1/accounts/authinfo",
):
    r = httpx.get(url, headers=HDR, timeout=30)
    print(f"GET {url} → HTTP {r.status_code}")
    if r.status_code == 200:
        b = r.json()
        print(f"  authenticated_user: {b.get('authenticatedUser', '')[:50]}")
        for ai in (b.get("accountIdentifiers") or [])[:12]:
            print(f"  账号: aggregator={ai.get('aggregator', '-')} "
                  f"merchant={ai.get('merchant', '-')}")
        break
    print(f"  {r.text[:200]}")
