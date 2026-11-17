# -*- coding: utf-8 -*-
"""GA4 爆品榜补查：item 维度须配 items 专用指标。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GA4_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30)
at = r.json()["access_token"]
PROP = os.environ.get("GA4_PROPERTY_ID", "313397200")
URL = (f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}"
       f":runReport")
HDR = {"Authorization": f"Bearer {at}"}
DR = {"startDate": "2020-01-01", "endDate": "2026-11-10"}


def rep(label, dim, mets, order, limit=12):
    resp = httpx.post(URL, headers=HDR, json={
        "dateRanges": [DR], "dimensions": [{"name": dim}],
        "metrics": [{"name": m} for m in mets],
        "orderBys": [{"metric": {"metricName": order}, "desc": True}],
        "limit": limit}, timeout=60)
    print(f"\n===== {label} =====")
    if resp.status_code != 200:
        print("[FAIL]", resp.text[:200])
        return
    for row in resp.json().get("rows", []):
        d = row["dimensionValues"][0]["value"]
        m = [x["value"] for x in row["metricValues"]]
        print(f"  {d[:66]:66} | " +
              " | ".join(f"{float(v):,.2f}" for v in m))


rep("品类收入榜", "itemCategory",
    ["itemRevenue", "itemsPurchased"], "itemRevenue")
rep("单品收入榜 top15", "itemName",
    ["itemRevenue", "itemsPurchased"], "itemRevenue", 15)
