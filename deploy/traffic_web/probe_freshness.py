# -*- coding: utf-8 -*-
"""量化 GA4 数据新鲜度：① runReport 当日数据落后多少分钟；② realtime API 可用维度/指标矩阵。"""
import datetime as dt
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
GA4 = "313397200"


def _tok() -> str:
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


AT = _tok()


def call(ep: str, body: dict):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}:{ep}",
        headers={"Authorization": f"Bearer {AT}",
                 "Content-Type": "application/json"},
        json=body, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code}: {r.text[:180]}")
    return r.json()


now = dt.datetime.now().replace(second=0, microsecond=0)
print(f"now = {now:%Y-%m-%d %H:%M} (Asia/Shanghai)")

# 1) runReport 当日最新有数据的分钟
j = call("runReport", {
    "dateRanges": [{"startDate": "today", "endDate": "today"}],
    "dimensions": [{"name": "dateHourMinute"}],
    "metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
    "orderBys": [{"dimension": {"dimensionName": "dateHourMinute"}}],
    "limit": 2000})
rows = j.get("rows", [])
print(f"\n[runReport today] 分钟行数={len(rows)}")
for r in rows[-5:]:
    v = r["dimensionValues"][0]["value"]
    m = [x["value"] for x in r["metricValues"]]
    ts = dt.datetime.strptime(v, "%Y%m%d%H%M")
    print(f"  {ts:%H:%M}  sessions={m[0]} activeUsers={m[1]}  (落后 {(now - ts).total_seconds()/60:.0f} 分钟)")
if rows:
    last = dt.datetime.strptime(rows[-1]["dimensionValues"][0]["value"], "%Y%m%d%H%M")
    print(f"  ==> runReport 当日数据延迟 ≈ {(now - last).total_seconds()/60:.0f} 分钟")

# 2) realtime 维度矩阵
DIMS = ["sessionSourceMedium", "sessionDefaultChannelGroup", "sessionSource",
        "sessionMedium", "country", "city", "deviceCategory",
        "landingPagePlusQueryString", "unifiedPagePathScreen", "pageLocation",
        "pageTitle", "eventName", "dateHourMinute", "streamId"]
print("\n[realtime dims] (配 activeUsers)")
ok_dims = []
for d in DIMS:
    try:
        j = call("runRealtimeReport", {
            "dimensions": [{"name": d}], "metrics": [{"name": "activeUsers"}],
            "limit": 1})
        ok_dims.append(d)
        print(f"  OK   {d} (rows={len(j.get('rows', []))})")
    except RuntimeError as e:
        print(f"  FAIL {d}: {e}")

# 3) realtime 指标矩阵
METS = ["activeUsers", "engagedSessions", "sessions", "eventCount",
        "screenPageViews", "keyEvents", "conversions", "userEngagementDuration",
        "newUsers", "totalUsers", "averageSessionDuration"]
print("\n[realtime metrics] (配 country)")
ok_mets = []
for m in METS:
    try:
        j = call("runRealtimeReport", {
            "dimensions": [{"name": "country"}], "metrics": [{"name": m}],
            "limit": 1})
        ok_mets.append(m)
        print(f"  OK   {m}")
    except RuntimeError as e:
        print(f"  FAIL {m}: {e}")

# 4) 无维度聚合（总数卡）
try:
    j = call("runRealtimeReport", {"metrics": [{"name": "activeUsers"},
                                               {"name": "sessions"}],
                                   "limit": 1})
    vals = [x["value"] for x in j.get("rows", [{}])[0].get("metricValues", [])]
    print(f"\n[realtime 无维度聚合] activeUsers={vals[0] if vals else '?'} sessions={vals[1] if len(vals) > 1 else '?'}")
except RuntimeError as e:
    print(f"\n[realtime 无维度聚合] FAIL: {e}")
