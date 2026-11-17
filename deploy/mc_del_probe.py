# -*- coding: utf-8 -*-
"""测 Merchant API products 删除端点的正确形态（拿死链样本试删）。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MC = "136469408"
BASE = f"https://merchantapi.googleapis.com/products/v1/accounts/{MC}"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HD = {"Authorization": f"Bearer {at}"}

# 1. 拿一个旧源死链样本（19 位纯数字 offer 的）
r = httpx.get(f"{BASE}/products", params={"pageSize": 250}, headers=HD,
              timeout=60)
sample = None
for p in r.json().get("products", []):
    if not p.get("offerId", "").startswith("shopify_"):
        sample = p
        break
if not sample:
    print("没找到旧源样本")
    raise SystemExit

pid = sample["name"].rsplit("/", 1)[-1]
b64 = sample.get("base64EncodedName", "")
print(f"样本: {pid[:60]}")
print(f"b64 : {b64[:60]}")

# 形态A: 原始 ~（httpx 不转义 ~）
rA = httpx.delete(f"{BASE}/products/{pid}", headers=HD, timeout=60)
print(f"\nA 原始~     → {rA.status_code} {rA.text[:120]!r}")

# 形态B: URL编码 %7E
from urllib.parse import quote
rB = httpx.delete(f"{BASE}/products/{quote(pid, safe='')}", headers=HD,
                  timeout=60)
print(f"B %7E编码    → {rB.status_code} {rB.text[:120]!r}")

# 形态C: base64EncodedName
if b64:
    rC = httpx.delete(f"{BASE}/products/{b64}", headers=HD, timeout=60)
    print(f"C base64名   → {rC.status_code} {rC.text[:120]!r}")

# 形态D: v1beta 端点原始~
rD = httpx.delete(
    f"https://merchantapi.googleapis.com/products/v1beta/accounts/{MC}"
    f"/products/{pid}", headers=HD, timeout=60)
print(f"D v1beta原始~ → {rD.status_code} {rD.text[:120]!r}")
