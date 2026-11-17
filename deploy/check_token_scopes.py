# -*- coding: utf-8 -*-
"""验证现有 refresh_token 的有效性与其覆盖的 scope（只读）。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

cid = os.environ["GOOGLE_CLIENT_ID"]
sec = os.environ["GOOGLE_CLIENT_SECRET"]
rt = os.environ["GOOGLE_REFRESH_TOKEN"]

# 1. 换 access_token
r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": cid,
    "client_secret": sec,
    "refresh_token": rt,
    "grant_type": "refresh_token",
}, timeout=30)
if r.status_code != 200:
    print(f"[失效] 换 token 失败: {r.status_code} {r.text[:200]}")
    raise SystemExit(1)
at = r.json()["access_token"]
print("[OK] refresh_token 有效，access_token 已刷新")

# 2. 查 scope 覆盖
info = httpx.get("https://oauth2.googleapis.com/tokeninfo",
                 params={"access_token": at}, timeout=30).json()
scopes = (info.get("scope") or "").split()
print(f"授权账号: {info.get('email', '?')}")
print(f"scope 覆盖 ({len(scopes)} 项):")
need = {
    "https://www.googleapis.com/auth/adwords": "Google Ads API",
    "https://www.googleapis.com/auth/analytics.readonly": "GA4 Data API(只读)",
    "https://www.googleapis.com/auth/analytics": "GA4 管理/写入",
}
for s in scopes:
    tag = need.get(s, "")
    mark = " <<< " + tag if tag else ""
    print(f"  - {s}{mark}")
print("\n判定:")
print(f"  Google Ads API : {'可用' if 'auth/adwords' in ' '.join(scopes) else '不可用'}")
print(f"  GA4 只读数据   : {'可用' if 'auth/analytics.readonly' in ' '.join(scopes) else '不可用'}")
