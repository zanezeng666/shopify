# -*- coding: utf-8 -*-
"""深挖：1) 全campaign清单 2) 商品级流量按campaign近5天(老系列做恢复传感器)
3) MC侧 adsLinks 状态(商品池为空的可疑根因)"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "unused"),
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", CID),
    "use_proto_plus": True,
})
gac = ads.get_service("GoogleAdsService")

print("=== 1) 全 campaign ===")
q1 = ("SELECT campaign.id, campaign.name, campaign.status, "
      "campaign.advertising_channel_type FROM campaign ORDER BY campaign.id")
camps = []
for row in gac.search(customer_id=CID, query=q1):
    c = row.campaign
    camps.append(c.id)
    print(f"  {c.id}  {c.status.name:9s} {c.advertising_channel_type.name:16s} {c.name}")

print("\n=== 2) 商品级流量按campaign近5天(老系列=恢复传感器) ===")
q2 = ("SELECT campaign.id, segments.date, metrics.impressions, metrics.clicks, "
      "metrics.cost_micros FROM shopping_performance_view "
      "WHERE segments.date DURING LAST_7_DAYS "
      "AND metrics.impressions > 0 ORDER BY segments.date DESC, campaign.id")
rows = list(gac.search(customer_id=CID, query=q2))
if not rows:
    print("  (近5天所有campaign都无商品级流量——Ads整体商品池仍空)")
for r in rows:
    print(f"  {r.segments.date} camp={r.campaign.id} imp={r.metrics.impressions} "
          f"clicks={r.metrics.clicks} cost=¥{r.metrics.cost_micros/1e6:.2f}")

# 再看老系列历史峰值作对照(11-01~11-08)
print("\n=== 2b) 老系列历史对照(11-03~11-08 有流量时段) ===")
q2b = ("SELECT campaign.id, segments.date, metrics.impressions "
       "FROM shopping_performance_view "
       "WHERE segments.date BETWEEN '2026-11-03' AND '2026-11-08' "
       "AND metrics.impressions > 0 ORDER BY segments.date")
for r in gac.search(customer_id=CID, query=q2b):
    print(f"  {r.segments.date} camp={r.campaign.id} imp={r.metrics.impressions}")

print("\n=== 3) MC 侧 adsLinks 状态 ===")
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
for view in ("FULL", None):
    url = f"https://merchantapi.googleapis.com/accounts/v1/accounts/136469408"
    if view:
        url += f"?view={view}"
    r = httpx.get(url, headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    if r.status_code == 200:
        j = r.json()
        print(f"  account keys: {sorted(j.keys())}")
        for key in ("adsLinks", "links"):
            for lk in (j.get(key) or []):
                print(f"  {key}: {dict(lk)}")
        break
    print(f"  [{view or 'default'}] {r.status_code}: {r.text[:200]}")
