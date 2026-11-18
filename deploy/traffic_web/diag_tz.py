# -*- coding: utf-8 -*-
"""诊断：GA4 property 时区 + today/yesterday 实况数据量。"""
import httpx
import os
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}"}

r = httpx.get("https://analyticsadmin.googleapis.com/v1beta/properties/313397200",
              headers=H, timeout=30)
print("property:", r.status_code, "timeZone=", r.json().get("timeZone"))

for d in ("today", "yesterday"):
    j = httpx.post(
        "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport",
        headers=H, json={
            "dateRanges": [{"startDate": d, "endDate": d}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}],
            "metrics": [{"name": "sessions"}], "limit": 20},
        timeout=60).json()
    rows = j.get("rows", [])
    tot = sum(int(x["metricValues"][0]["value"]) for x in rows)
    print(f"\n[{d}] sessions={tot} rows={len(rows)}")
    for x in rows[:6]:
        print("   ", x["dimensionValues"][0]["value"],
              x["metricValues"][0]["value"])

# 明确按日期查（property 时区的昨天=11-17 与 11-16）
for d in ("2026-11-17", "2026-11-18"):
    j = httpx.post(
        "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport",
        headers=H, json={
            "dateRanges": [{"startDate": d, "endDate": d}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}],
            "metrics": [{"name": "sessions"}], "limit": 20},
        timeout=60).json()
    rows = j.get("rows", [])
    tot = sum(int(x["metricValues"][0]["value"]) for x in rows)
    print(f"\n[{d}] sessions={tot} rows={len(rows)}")
