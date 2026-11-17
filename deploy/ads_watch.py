# -*- coding: utf-8 -*-
"""每日观察快照：PMax 表现+strength / GA4 付费流量国家分布+关键事件 / MC 免费位。
输出 logs/ads_watch_YYYYMMDD.txt（cron 08:00 服务器时区）。"""
import datetime as dt
import os
from collections import Counter

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
GA4 = "313397200"
MID = "136469408"
OUT = (f"/home/jason/shopify-admin/logs/ads_watch_"
       f"{dt.date.today():%Y%m%d}.txt")
os.makedirs("/home/jason/shopify-admin/logs", exist_ok=True)
buf = []
p = buf.append
p(f"=== Ads 每日观察 {dt.date.today()} ===")

# --- Ads: PMax 昨日 + strength ---
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, metrics.cost_micros, metrics.clicks, "
    "metrics.impressions, metrics.conversions, "
    "metrics.conversions_from_interactions_rate "
    "FROM campaign WHERE campaign.status='ENABLED' "
    "AND segments.date DURING YESTERDAY"))
p("\n[昨日投放]")
for r in rows:
    m = r.metrics
    p(f"  {r.campaign.name[:30]:<30} ${m.cost_micros/1e6:.2f} "
      f"clicks={m.clicks} imps={m.impressions} conv={m.conversions:.1f}")
rows = gas.search(customer_id=CID, query=(
    "SELECT asset_group.ad_strength FROM asset_group "
    "WHERE campaign.status='ENABLED'"))
for r in rows:
    p(f"[PMax strength] {r.asset_group.ad_strength.name}")

# --- GA4: 昨日付费流量国家 + 关键事件 ---
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}


def runreport(body):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}"
        ":runReport", headers=H, json=body, timeout=60)
    return r.json() if r.status_code == 200 else {"err": r.text[:150]}


j = runreport({
    "dateRanges": [{"startDate": "yesterday", "endDate": "yesterday"}],
    "dimensions": [{"name": "country"}],
    "metrics": [{"name": "sessions"}],
    "dimensionFilter": {"filter": {
        "fieldName": "sessionDefaultChannelGroup",
        "inListFilter": {"values": ["Paid Search", "Paid Shopping",
                                    "Paid Video"]}}},
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    "limit": 8})
p("\n[昨日付费流量国家分布]")
if "rows" in j:
    for row in j["rows"]:
        p(f"  {row['dimensionValues'][0]['value']:<22} "
          f"{row['metricValues'][0]['value']}")
else:
    p(f"  (无数据或异常: {j.get('err', j.get('rowCount', 0))})")

j2 = runreport({
    "dateRanges": [{"startDate": "yesterday", "endDate": "yesterday"}],
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "eventCount"}],
    "dimensionFilter": {"filter": {
        "fieldName": "eventName",
        "inListFilter": {"values": ["add_to_cart", "generate_lead",
                                    "purchase", "begin_checkout"]}}}})
p("[关键事件(全渠道)]")
if "rows" in j2:
    for row in j2["rows"]:
        p(f"  {row['dimensionValues'][0]['value']:<14} "
          f"{row['metricValues'][0]['value']}")
else:
    p(f"  (无: {j2.get('err', '0 events')})")

# --- MC 免费位状态 ---
r = httpx.get(
    f"https://shoppingcontent.googleapis.com/content/v2.1/{MID}"
    "/freelistingsprogram", headers=H, timeout=30)
if r.status_code == 200:
    g = r.json().get("globalState", "?")
    regions = [(s.get("regionCodes"), s.get("eligibilityStatus"))
               for s in r.json().get("regionStatuses", [])]
    p(f"[MC 免费位] {g} {regions}")
else:
    p(f"[MC 免费位] API {r.status_code}（sunset 端点不稳定，忽略）")

text = "\n".join(buf)
print(text)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(text + "\n")
