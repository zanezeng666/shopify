# -*- coding: utf-8 -*-
"""A2) PMax Medical 转化按动作拆分（不带 date segment）
GA4 补刀) 付费渠道 keyEvents 按事件名拆分（直接定性）。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
API = "https://googleads.googleapis.com/v26/customers/7059800494"


def ga(q):
    r = httpx.post(f"{API}/googleAds:searchStream",
                   headers=H, json={"query": q}, timeout=60)
    if r.status_code != 200:
        print(f"  [HTTP {r.status_code}] {r.text[:200]}")
        return []
    j = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for b in j:
        out += b.get("results", [])
    return out


print("=== A2) PMax Medical Estry 转化按动作拆分（全部历史） ===")
rows = ga(
    "SELECT conversion_action.name, conversion_action.category, "
    "metrics.conversions, metrics.all_conversions "
    "FROM campaign WHERE campaign.name LIKE '%Medical Estry%' "
    "ORDER BY metrics.conversions DESC")
for e in rows:
    a, m = e["conversionAction"], e.get("metrics", {})
    n = float(m.get("conversions", 0))
    if n:
        print(f"   转化{n:>5.0f}/全{float(m.get('allConversions',0)):>5.0f}  "
              f"{a['name'][:46]:<46} cat={a.get('category','')[:18]}")
if not any(float(e.get("metrics", {}).get("conversions", 0)) for e in rows):
    print("   (拆分查询无结果)")

print("\n=== GA4) 付费渠道 keyEvents 按事件名 (11-01~15) ===")
GP = "https://analyticsdata.googleapis.com/v1beta/properties/313397200"
r = httpx.post(f"{GP}:runReport", headers=H, timeout=120, json={
    "dateRanges": [{"startDate": "2026-11-01", "endDate": "2026-11-15"}],
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "keyEvents"}],
    "dimensionFilter": {"filter": {
        "fieldName": "sessionDefaultChannelGroup",
        "inListFilter": {"values": ["Paid Search", "Cross-network", "Paid Shopping"]}}},
    "orderBys": [{"metric": {"metricName": "keyEvents"}, "desc": True}]})
if r.status_code != 200:
    print(f"  GA4 {r.status_code}: {r.text[:200]}")
else:
    for row in r.json().get("rows", []):
        print(f"   {row['dimensionValues'][0]['value'][:36]:<36}"
              f" keyEvents={row['metricValues'][0]['value']}")
