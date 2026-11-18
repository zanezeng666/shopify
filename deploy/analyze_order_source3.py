"""收口：① 全 campaign id 对照 24452460184 ② GA4 purchase 时间线 ③ kangaroo 页今日流量来源。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx
from google.ads.googleads.client import GoogleAdsClient

CID = "7059800494"
GA4 = "313397200"
TARGET = "24452460184"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

r = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.advertising_channel_type "
    "FROM campaign WHERE campaign.status = 'ENABLED'"))
hit = None
for row in r:
    c = row.campaign
    mark = " <== 目标" if str(c.id) == TARGET else ""
    if mark or "Medical" in c.name or "PMax" in c.name or "Performance" in c.name:
        print(f"  {c.id} {c.name[:40]!r} {c.advertising_channel_type.name}{mark}")
        if mark:
            hit = c
print(f"目标 campaign 在账号内: {hit is not None}（共 {r.total_results_count if hasattr(r,'total_results_count') else '?'} 个 ENABLED）")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}:runReport"


def rep(body, tag):
    j = httpx.post(URL, headers=H, json=body, timeout=60).json()
    print(f"\n[{tag}]" if "rows" in j else f"[{tag}] 无: {j.get('err', j.get('rowCount', 0))}")
    for row in (j.get("rows") or []):
        vals = [d["value"] for d in row["dimensionValues"]] + [m["value"] for m in row["metricValues"]]
        print("  " + " | ".join(vals))


rep({"dateRanges": [{"startDate": "2026-11-15", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "dateHour"}, {"name": "landingPagePlusQueryString"}],
     "metrics": [{"name": "eventCount"}, {"name": "purchaseRevenue" if True else "revenue"}],
     "dimensionFilter": {"filter": {"fieldName": "eventName", "stringFilter": {"value": "purchase"}}},
     "limit": 10}, "purchase 时间线(11-15~18)")

rep({"dateRanges": [{"startDate": "2026-11-18", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "sessionDefaultChannelGroup"}],
     "metrics": [{"name": "sessions"}, {"name": "eventCount"}],
     "dimensionFilter": {"filter": {"fieldName": "landingPagePlusQueryString",
                                    "stringFilter": {"value": "/products/battery-for-cardinalhealth", "matchType": "BEGINS_WITH"}}},
     "limit": 6}, "kangaroo 页今日会话来源")
