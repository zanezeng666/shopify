"""GA4 付费会话的 campaign 名称清单（11-13~18）：识别非主账户 campaign。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport"


def rep(body, tag):
    j = httpx.post(URL, headers=H, json=body, timeout=60).json()
    print(f"[{tag}]" if j.get("rows") else f"[{tag}] 无: {j.get('err', j.get('rowCount', 0))}")
    for row in j.get("rows") or []:
        vals = [d["value"] for d in row["dimensionValues"]] + [m["value"] for m in row["metricValues"]]
        print("  " + " | ".join(vals))
    print()


rep({"dateRanges": [{"startDate": "2026-11-13", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "sessionCampaign"}],
     "metrics": [{"name": "sessions"}],
     "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}], "limit": 15},
    "会话 campaign 名称（全渠道 11-13~18）")

rep({"dateRanges": [{"startDate": "2026-11-13", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "sessionCampaign"}, {"name": "sessionDefaultChannelGroup"}],
     "metrics": [{"name": "sessions"}],
     "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup",
                                    "inListFilter": {"values": ["Paid Search", "Paid Shopping",
                                                                "Paid Video", "Cross-network",
                                                                "Display"]}}},
     "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}], "limit": 15},
    "付费会话 campaign×渠道")
