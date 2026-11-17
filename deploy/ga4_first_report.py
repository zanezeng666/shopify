# -*- coding: utf-8 -*-
"""GA4 Data API 首拉实测（property 313397200，近2天会话/转化）。"""
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

resp = httpx.post(
    "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport",
    headers={"Authorization": f"Bearer {at}"},
    json={
        "dateRanges": [{"startDate": "2026-11-09", "endDate": "2026-11-10"}],
        "dimensions": [{"name": "date"}],
        "metrics": [{"name": "sessions"}, {"name": "totalAdRevenue"},
                    {"name": "conversions"}],
        "limit": 10,
    }, timeout=60)

if resp.status_code != 200:
    print(f"[FAIL] {resp.status_code}: {resp.text[:300]}")
    raise SystemExit(0)

data = resp.json()
rows = data.get("rows", [])
print("[OK] GA4 Data API 拉数成功！近 2 天:")
for row in rows:
    dims = ",".join(d["value"] for d in row.get("dimensionValues", []))
    mets = {m.get("name", ""): mv["value"] for m, mv in zip(
        [dict(name=n) for n in ("sessions", "totalAdRevenue", "conversions")],
        row.get("metricValues", []))}
    print(f"  {dims}: sessions={mets.get('sessions')} "
          f"adRevenue={mets.get('totalAdRevenue')} conv={mets.get('conversions')}")

# 存 property id 到 .env（幂等追加）
ENV_PATH = "/home/jason/shopify-admin/.env"
lines = open(ENV_PATH).read().splitlines()
if not any(l.startswith("GA4_PROPERTY_ID=") for l in lines):
    with open(ENV_PATH, "a") as f:
        f.write("\nGA4_PROPERTY_ID=313397200\n")
    print("[OK] 已写入 .env: GA4_PROPERTY_ID=313397200")
else:
    print("[SKIP] GA4_PROPERTY_ID 已存在")
