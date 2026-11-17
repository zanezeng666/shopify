# -*- coding: utf-8 -*-
"""两周复盘报告：修复前(11-01~15) vs 修复后(11-16~30) 核心指标对比。
决策依据输出：Bing 复制 / 再营销启动 / 免费位效果。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
GA4 = "313397200"
OUT = "/home/jason/shopify-admin/logs/ads_review_20261130.txt"
buf = []
p = buf.append
p("=== 两周复盘（2026-11-30）：修复前 vs 修复后 ===\n")

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

for label, d1, d2 in (("修复前 11-01~15", "2026-11-01", "2026-11-15"),
                      ("修复后 11-16~30", "2026-11-16", "2026-11-30")):
    rows = gas.search(customer_id=CID, query=(
        f"SELECT campaign.advertising_channel_type, metrics.cost_micros, "
        "metrics.clicks, metrics.conversions FROM campaign "
        f"WHERE segments.date BETWEEN '{d1}' AND '{d2}' "
        "AND campaign.status != 'REMOVED'"))
    agg = {}
    for r in rows:
        t = r.campaign.advertising_channel_type.name
        c, k, v = agg.get(t, (0, 0, 0.0))
        agg[t] = (c + r.metrics.cost_micros / 1e6, k + r.metrics.clicks,
                  v + r.metrics.conversions)
    p(f"[{label} Ads]")
    for t, (c, k, v) in sorted(agg.items()):
        p(f"  {t:<16} ${c:>7.2f} clicks={k:<6} conv={v:.1f}")
    p("")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

for label, d1, d2 in (("修复前", "2026-11-01", "2026-11-15"),
                      ("修复后", "2026-11-16", "2026-11-30")):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}"
        ":runReport", headers=H, json={
            "dateRanges": [{"startDate": d1, "endDate": d2}],
            "dimensions": [{"name": "country"}],
            "metrics": [{"name": "sessions"}],
            "dimensionFilter": {"filter": {
                "fieldName": "sessionDefaultChannelGroup",
                "inListFilter": {"values": ["Paid Search", "Paid Shopping",
                                            "Paid Video"]}}},
            "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
            "limit": 6}, timeout=60)
    p(f"[{label} GA4 付费会话国家]")
    total = us = 0
    if r.status_code == 200:
        for row in r.json().get("rows", []):
            n = int(row["metricValues"][0]["value"])
            total += n
            if row["dimensionValues"][0]["value"] == "United States":
                us = n
            p(f"  {row['dimensionValues'][0]['value']:<22} {n}")
    p(f"  → US 占比: {us}/{total} = {100*us/max(total,1):.0f}%\n")

for label, d1, d2 in (("修复前", "2026-11-01", "2026-11-15"),
                      ("修复后", "2026-11-16", "2026-11-30")):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}"
        ":runReport", headers=H, json={
            "dateRanges": [{"startDate": d1, "endDate": d2}],
            "dimensions": [{"name": "eventName"}],
            "metrics": [{"name": "eventCount"}, {"name": "sessions"}],
            "dimensionFilter": {"filter": {
                "fieldName": "eventName",
                "inListFilter": {"values": ["add_to_cart",
                                            "begin_checkout", "purchase",
                                            "generate_lead"]}}}},
        timeout=60)
    p(f"[{label} 关键事件]")
    if r.status_code == 200:
        for row in r.json().get("rows", []):
            p(f"  {row['dimensionValues'][0]['value']:<14} "
              f"{row['metricValues'][0]['value']}")
    else:
        p("  (无数据)")
    p("")

p("=== 决策规则 ===")
p("Bing 复制启动条件: 修复后 US 会话≥600 且 add_to_cart≥20")
p("再营销启动条件: 全渠道月会话≥5,000（列表可攒到 1,000+）")
p("免费位效果: 修复后 Organic Shopping 会话对比（见 GA4 渠道报告）")
text = "\n".join(buf)
print(text)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(text + "\n")
