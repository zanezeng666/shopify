# -*- coding: utf-8 -*-
"""MC API 实测（content scope）：账号列表拿 MC ID + 商品列表第一页看结构。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

tr = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()
at = tr["access_token"]
print(f"token scope: {tr.get('scope')}")
HDR = {"Authorization": f"Bearer {at}"}

# ---- 1. Content API accounts（列出授权用户可访问的 MC 账号）----
print("\n=== Content API /accounts ===")
r = httpx.get("https://shoppingcontent.googleapis.com/v2.1/accounts",
              headers=HDR, timeout=30)
print(f"  HTTP {r.status_code}")
try:
    for a in (r.json().get("resources") or []):
        print(f"  MC {a.get('id')} | {a.get('name')} | "
              f"seller_id={a.get('sellerId', '')[:20]}")
    if r.json().get("error"):
        print(f"  error: {r.json()['error'].get('message', '')[:220]}")
except Exception as e:  # noqa
    print(f"  解析失败: {e} | {r.text[:200]}")

# ---- 2. merchantapi accounts 列表（备用）----
print("\n=== merchantapi accounts list ===")
r2 = httpx.get("https://merchantapi.googleapis.com/accounts/v1beta/accounts",
               headers=HDR, timeout=30)
print(f"  HTTP {r2.status_code}")
try:
    b = r2.json()
    for a in (b.get("accounts") or [])[:10]:
        print(f"  {a.get('name')} | {a.get('accountName', '')[:30]}")
    if b.get("error"):
        print(f"  error: {b['error'].get('message', '')[:220]}")
except Exception as e:  # noqa
    print(f"  解析失败: {e} | {r2.text[:200]}")
