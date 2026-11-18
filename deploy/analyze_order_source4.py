"""终局收口：① 24452460184 不限状态 ② kangaroo 页 3 天会话渠道 ③ GA4 时区。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx
from google.ads.googleads.client import GoogleAdsClient

CID = "7059800494"
GA4 = "313397200"
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# 不限 status 直查目标 id
try:
    r = gas.search(customer_id=CID, query=(
        "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type, "
        "campaign.start_date FROM campaign WHERE campaign.id = 24452460184"))
    found = list(r)
    if found:
        for row in found:
            c = row.campaign
            print(f"[目标] {c.id} {c.name!r} status={c.status.name} type={c.advertising_channel_type.name} start={c.start_date}")
    else:
        print("[目标] 本账号任何状态均无此 id → 来自其他 Ads 账户")
except Exception as e:
    print(f"[目标] 查询失败: {str(e)[:200]}")

# 相邻 id 段的 campaign（看 24452xxxxx 段是谁）
r2 = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.status FROM campaign"))
ids = sorted((row.campaign.id, row.campaign.name, row.campaign.status.name) for row in r2)
print(f"账号全部 campaign {len(ids)} 个，id 范围 {ids[0][0]} ~ {ids[-1][0]}")
for i in ids:
    if str(i[0]).startswith("24452"):
        print(f"  相邻段: {i}")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}:runReport"

j = httpx.post(URL, headers=H, json={"entity": {"propertyId": GA4}}, timeout=30)  # 预期 404，换 metadata
j = httpx.get(f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}/audiences?pageSize=1",
              headers={"Authorization": f"Bearer {at}"}, timeout=30)
# 用 admin API 拿 property 时区最直接
j = httpx.get(f"https://analyticsadmin.googleapis.com/v1beta/properties/{GA4}",
              headers={"Authorization": f"Bearer {at}"}, timeout=30)
if j.status_code == 200:
    print(f"GA4 时区: {j.json().get('timeZone')}  名称: {j.json().get('displayName')}")
else:
    print(f"GA4 admin API: {j.status_code} {j.text[:100]}")


def rep(body, tag):
    r_ = httpx.post(URL, headers=H, json=body, timeout=60).json()
    print(f"\n[{tag}]" if r_.get("rows") else f"\n[{tag}] 无: {r_.get('err', r_.get('rowCount', 0))}")
    for row in r_.get("rows") or []:
        vals = [d["value"] for d in row["dimensionValues"]] + [m["value"] for m in row["metricValues"]]
        print("  " + " | ".join(vals))


rep({"dateRanges": [{"startDate": "2026-11-16", "endDate": "2026-11-18"}],
     "dimensions": [{"name": "date"}, {"name": "sessionDefaultChannelGroup"}],
     "metrics": [{"name": "sessions"}, {"name": "eventCount"}],
     "dimensionFilter": {"filter": {"fieldName": "landingPagePlusQueryString",
                                    "stringFilter": {"value": "/products/battery-for-cardinalhealth", "matchType": "BEGINS_WITH"}}},
     "orderBys": [{"dimension": {"dimensionName": "date"}}], "limit": 15}, "kangaroo 页会话渠道(11-16~18)")
