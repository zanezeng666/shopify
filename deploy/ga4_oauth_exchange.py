# -*- coding: utf-8 -*-
"""尝试用用户提供的授权码换 GA4 refresh_token；成功则存 .env 并验证。"""
import os
import urllib.parse

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID_ = os.environ["GOOGLE_CLIENT_ID"]
SEC = os.environ["GOOGLE_CLIENT_SECRET"]
CODE = "4/0AUn6Hd_LbiIvJlrJ0mhKpltqqQlrztIRVXDalrU7O_YLOZ7h1S1BQlvKtwkzYJ7nUE-IyA"
ENV_PATH = "/home/jason/shopify-admin/.env"

token = None
errs = []
for redirect_uri in ("http://localhost:8080/oauth2callback",
                     "http://localhost:8080", "urn:ietf:wg:oauth:2.0:oob"):
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": CID_,
        "client_secret": SEC,
        "code": CODE,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }, timeout=30)
    if r.status_code == 200:
        token = r.json()
        print(f"[OK] 授权码有效！redirect_uri={redirect_uri}")
        break
    errs.append(f"{redirect_uri} -> {r.status_code}: "
                f"{r.json().get('error_description', r.json().get('error'))[:120]}")

if not token:
    print("[FAIL] 授权码换不到凭证，原因逐条如下:")
    for e in errs:
        print("  -", e)
    # 生成新授权链接
    url = ("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": CID_,
        "redirect_uri": "http://localhost:8080/oauth2callback",
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/analytics.readonly",
        "access_type": "offline",
        "prompt": "consent",
    }))
    print("\n>> 请重新走一遍授权（操作同前），复制新 code 发我:")
    print(url)
    raise SystemExit(0)

# 成功：存入 .env（GA4_REFRESH_TOKEN，不覆盖现有变量）
rt = token.get("refresh_token")
print(f"access_token: {token['access_token'][:20]}...")
print(f"scope: {token.get('scope')}")
if not rt:
    print("[WARN] 响应无 refresh_token（授权时未带 offline），"
          "需重走授权")
    raise SystemExit(0)
print(f"refresh_token: {rt[:15]}...")

lines = open(ENV_PATH).read().splitlines()
if any(l.startswith("GA4_REFRESH_TOKEN=") for l in lines):
    lines = [l if not l.startswith("GA4_REFRESH_TOKEN=")
             else f"GA4_REFRESH_TOKEN={rt}" for l in lines]
    body = "\n".join(lines) + "\n"
else:
    body = "\n".join(lines) + f"\nGA4_REFRESH_TOKEN={rt}\n"
with open(ENV_PATH, "w") as f:
    f.write(body)
print("[OK] 已写入 .env: GA4_REFRESH_TOKEN")

# 验证：换 access_token 查 scope
r2 = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": CID_, "client_secret": SEC,
    "refresh_token": rt, "grant_type": "refresh_token"}, timeout=30)
if r2.status_code == 200:
    at = r2.json()["access_token"]
    info = httpx.get("https://oauth2.googleapis.com/tokeninfo",
                     params={"access_token": at}, timeout=30).json()
    print(f"[验证] scope: {info.get('scope')}")
    print("[验证] refresh_token 可用，GA4 数据接入就绪")
    print("\n下一步只差: GA4 Property ID（纯数字，analytics.google.com 后台"
          "管理→属性设置）发我即可开始拉数")
else:
    print("[FAIL] refresh_token 复验失败:", r2.text[:200])
