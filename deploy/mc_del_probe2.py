# -*- coding: utf-8 -*-
"""测 :delete 自定义方法形态。"""
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

r = httpx.get(f"{BASE}/products", params={"pageSize": 250}, headers=HD,
              timeout=60)
pid = next(p["name"].rsplit("/", 1)[-1]
           for p in r.json()["products"]
           if not p.get("offerId", "").startswith("shopify_"))
print(f"样本: {pid[:60]}")

# E: v1 自定义方法
rE = httpx.post(f"{BASE}/products/{pid}:delete", headers=HD, timeout=60)
print(f"E v1 :delete      → {rE.status_code} {rE.text[:140]!r}")

# F: v1beta 自定义方法
rF = httpx.post(
    f"https://merchantapi.googleapis.com/products/v1beta/accounts/{MC}"
    f"/products/{pid}:delete", headers=HD, timeout=60)
print(f"F v1beta :delete  → {rF.status_code} {rF.text[:140]!r}")

# G: v2beta 自定义方法
rG = httpx.post(
    f"https://merchantapi.googleapis.com/products/v2beta/accounts/{MC}"
    f"/products/{pid}:delete", headers=HD, timeout=60)
print(f"G v2beta :delete  → {rG.status_code} {rG.text[:140]!r}")
