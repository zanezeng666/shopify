"""订单 #2241 来源深挖：① Ads campaign 24452460184 身份+近3日表现 ② GA4 purchase 会话归因。只读。"""
import os
import sys

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx
from google.ads.googleads.client import GoogleAdsClient

CID = "7059800494"
GA4 = "313397200"

# --- ① Ads: campaign 身份 + 近 3 日表现 ---
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

r = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type "
    "FROM campaign WHERE campaign.id = 24452460184"))
for row in r:
    c = row.campaign
    print(f"[Campaign] id={c.id} name={c.name!r} status={c.status.name} type={c.advertising_channel_type.name}")

r2 = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, segments.date, metrics.cost_micros, metrics.clicks, "
    "metrics.impressions, metrics.conversions, metrics.conversions_value "
    f"FROM campaign WHERE campaign.id = 24452460184 AND segments.date BETWEEN '2026-11-16' AND '2026-11-18'"))
for row in r2:
    m = row.metrics
    print(f"  {row.segments.date}: ¥{m.cost_micros/1e6:.2f} clicks={m.clicks} "
          f"imps={m.impressions} conv={m.conversions:.1f} conv_value=${m.conversions_value:.2f}")

# --- ② GA4: purchase 会话归因 ---
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}:runReport"


def rep(body, tag):
    j = httpx.post(URL, headers=H, json=body, timeout=60).json()
    print(f"\n[{tag}]" if "rows" in j else f"[{tag}] 无数据: {j.get('err', j.get('rowCount', 0))}")
    for row in (j.get("rows") or []):
        dims = [d["value"] for d in row["dimensionValues"]]
        mets = [m["value"] for m in row["metricValues"]]
        print("  " + " | ".join(dims + mets))


# purchase 事件按 transactionId（覆盖 11-16~18 防 GA4 时区差）
rep({"dateRanges": [{"startDate": "2026-11-16", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "transactionId"}, {"name": "sessionSource"},
                    {"name": "sessionMedium"}, {"name": "sessionDefaultChannelGroup"}],
     "metrics": [{"name": "revenue"}],
     "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "purchase"}}},
     "limit": 10}, "GA4 purchase 会话")

# 同会话细节：国家/设备/落地页/campaign
rep({"dateRanges": [{"startDate": "2026-11-16", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "country"}, {"name": "deviceCategory"}, {"name": "landingPagePlusQueryString"}],
     "metrics": [{"name": "sessions"}],
     "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "purchase"}}},
     "limit": 5}, "GA4 purchase 会话细节")

# 今日全站渠道概览（背景）
rep({"dateRanges": [{"startDate": "2026-11-18", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "sessionDefaultChannelGroup"}],
     "metrics": [{"name": "sessions"}, {"name": "conversions"}],
     "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}], "limit": 8}, "今日(11-18)全站渠道")
