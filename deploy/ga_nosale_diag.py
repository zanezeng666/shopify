# -*- coding: utf-8 -*-
"""GA4 诊断：近两周出单断点分析
A) 按日全站漏斗 sessions→加购→结账→购买→收入
B) 健康周(11-01~07) vs 病周(11-08~13) 按渠道对比
C) Ads 流量(google/cpc)按日质量
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
PROP = "313397200"
API = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}"

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def run(body):
    r = httpx.post(f"{API}:runReport", json=body, headers=H, timeout=120)
    if r.status_code != 200:
        raise SystemExit(f"GA4 {r.status_code}: {r.text[:300]}")
    return r.json()


def show(j, dims):
    hdr = j.get("dimensionHeaders", [])
    mhdr = [m["name"] for m in j.get("metricHeaders", [])]
    rows = j.get("rows", [])
    print("  " + " | ".join([d["name"] for d in hdr] + mhdr))
    for r in rows:
        print("  " + " | ".join(
            [dv["value"] for dv in r["dimensionValues"]]
            + [mv["value"] for mv in r["metricValues"]]))
    if not rows:
        print("  (无数据)")


print("=== A) 按日全站漏斗 (10/30 - 11/13) ===")
show(run({
    "dateRanges": [{"startDate": "2026-10-30", "endDate": "2026-11-13"}],
    "dimensions": [{"name": "date"}],
    "metrics": [{"name": "sessions"}, {"name": "addToCarts"},
                {"name": "checkouts"}, {"name": "ecommercePurchases"},
                {"name": "purchaseRevenue"}],
    "orderBys": [{"dimension": {"dimensionName": "date"}}],
}), 1)

print("\n=== B) 健康周(11-01~07) vs 病周(11-08~13) 按渠道 ===")
show(run({
    "dateRanges": [
        {"name": "健康周", "startDate": "2026-11-01", "endDate": "2026-11-07"},
        {"name": "病周", "startDate": "2026-11-08", "endDate": "2026-11-13"}],
    "dimensions": [{"name": "sessionDefaultChannelGroup"}],
    "metrics": [{"name": "sessions"}, {"name": "ecommercePurchases"},
                {"name": "purchaseRevenue"}],
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
}), 2)

print("\n=== C) Ads 流量(google/cpc) 按日: 量还在但质如何 ===")
show(run({
    "dateRanges": [{"startDate": "2026-11-01", "endDate": "2026-11-13"}],
    "dimensions": [{"name": "date"}],
    "metrics": [{"name": "sessions"}, {"name": "addToCarts"},
                {"name": "ecommercePurchases"}, {"name": "purchaseRevenue"}],
    "dimensionFilter": {
        "filter": {
            "fieldName": "sessionSourceMedium",
            "inListFilter": {
                "values": ["google / cpc", "google / pmax"]}},
    },
    "orderBys": [{"dimension": {"dimensionName": "date"}}],
}), 1)
