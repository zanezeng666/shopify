# -*- coding: utf-8 -*-
"""用 GA4 凭证列出账号下的属性（找 bomibattery Property ID）。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GA4_REFRESH_TOKEN"],
    "grant_type": "refresh_token",
}, timeout=30)
at = r.json()["access_token"]

resp = httpx.get(
    "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
    headers={"Authorization": f"Bearer {at}"},
    params={"pageSize": 50}, timeout=30)
if resp.status_code != 200:
    print("[FAIL]", resp.status_code, resp.text[:300])
    raise SystemExit(0)

print("=== GA4 账号 / 属性一览 ===")
for acc in resp.json().get("accountSummaries", []):
    print(f"账号: {acc.get('displayName')} ({acc.get('name','').split('/')[-1]})")
    for p in acc.get("propertySummaries", []):
        pid = p.get("name", "").split("/")[-1]
        print(f"  属性: {p.get('displayName')} | ID={pid} | "
              f"type={p.get('propertyType','?')}")
if not resp.json().get("accountSummaries"):
    print("（该授权账号下没有可见的 GA4 属性）")
