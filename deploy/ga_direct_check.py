# -*- coding: utf-8 -*-
"""Direct 巨量流量拆解：落地页/地域/设备——判断是否 bot"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
PROP = "313397200"
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
API = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}"


def run(body):
    r = httpx.post(f"{API}:runReport", json=body, headers=H, timeout=120)
    if r.status_code != 200:
        raise SystemExit(f"GA4 {r.status_code}: {r.text[:250]}")
    return r.json()


def show(j):
    for r in j.get("rows", []):
        print("  " + " | ".join(
            [dv["value"] for dv in r["dimensionValues"]]
            + [mv["value"] for mv in r["metricValues"]]))


DIRECT = {"filter": {"fieldName": "sessionDefaultChannelGroup",
                     "stringFilter": {"matchType": "EXACT", "value": "Direct"}}}
DR = [{"startDate": "2026-11-01", "endDate": "2026-11-13"}]

print("=== Direct 流量 Top 落地页 (11-01~13) ===")
show(run({"dateRanges": DR, "dimensions": [{"name": "landingPagePlusQueryString"}],
          "metrics": [{"name": "sessions"}, {"name": "engagedSessions"},
                      {"name": "ecommercePurchases"}],
          "dimensionFilter": DIRECT,
          "limit": 12, "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}]}))

print("\n=== Direct 流量按国家 ===")
show(run({"dateRanges": DR, "dimensions": [{"name": "country"}],
          "metrics": [{"name": "sessions"}, {"name": "engagedSessions"}],
          "dimensionFilter": DIRECT, "limit": 10,
          "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}]}))

print("\n=== Direct 流量按设备+语言(前10) ===")
show(run({"dateRanges": DR,
          "dimensions": [{"name": "deviceCategory"}, {"name": "language"}],
          "metrics": [{"name": "sessions"}, {"name": "engagedSessions"}],
          "dimensionFilter": DIRECT, "limit": 10,
          "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}]}))
