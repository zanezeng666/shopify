# -*- coding: utf-8 -*-
"""GA4 Data API 验证 + 广告渠道效果首报（近7天，按渠道/广告系列）。"""
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
PROP = os.environ.get("GA4_PROPERTY_ID", "313397200")

resp = httpx.post(
    f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}:runReport",
    headers={"Authorization": f"Bearer {at}"},
    json={
        "dateRanges": [{"startDate": "2026-11-04", "endDate": "2026-11-10"}],
        "dimensions": [{"name": "sessionDefaultChannelGroup"},
                       {"name": "sessionCampaignName"}],
        "metrics": [{"name": "sessions"}, {"name": "conversions"},
                    {"name": "purchaseRevenue"}, {"name": "totalAdRevenue"}],
        "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
        "limit": 20,
    }, timeout=60)

if resp.status_code != 200:
    print(f"[FAIL] {resp.status_code}: {resp.text[:300]}")
    raise SystemExit(0)

data = resp.json()
hdr = [d["name"] for d in data.get("dimensionHeaders", [])]
print(f"[OK] GA4 Data API 已通！{hdr}")
print(f"\n近 7 天（11-04 ~ 11-10）按渠道×广告系列:")
print(f"{'渠道':18} {'广告系列':32} {'会话':>6} {'转化':>5} {'购买收入':>10} {'广告收入':>9}")
for row in data.get("rows", []):
    dims = [d["value"] for d in row["dimensionValues"]]
    m = [v["value"] for v in row["metricValues"]]
    print(f"{dims[0][:18]:18} {dims[1][:32]:32} "
          f"{m[0]:>6} {m[1]:>5} {m[2]:>4} {m[3]:>9}")
