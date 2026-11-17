# -*- coding: utf-8 -*-
"""全量 campaign 清单(已验证字段集) + 状态统计。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}",
     "Content-Type": "application/json"}

q = ("SELECT campaign.id, campaign.name, campaign.status, "
     "campaign.advertising_channel_type, "
     "metrics.cost_micros, metrics.clicks, metrics.impressions "
     "FROM campaign WHERE campaign.status != 'REMOVED'")
stat = {}
for cid in ("7059800494", "2214926660", "1651348739"):
    print(f"\n===== 账号 {cid} =====")
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{cid}/"
        "googleAds:searchStream", headers=H, json={"query": q}, timeout=30)
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    for batch in rows:
        for e in batch.get("results", []):
            c, m = e["campaign"], e.get("metrics", {})
            stat[c["status"]] = stat.get(c["status"], 0) + 1
            print(f"  [{c['status']:>7}] {c['id']} "
                  f"{c['name'][:46]:<46} {c['advertisingChannelType']:<9}"
                  f" | 花${int(m.get('costMicros',0))/1e6:>7.1f} "
                  f"点击{m.get('clicks',0):>6} "
                  f"曝光{int(m.get('impressions',0)):>9,}")
print("\n状态统计:", stat)
