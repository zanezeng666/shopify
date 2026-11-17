# -*- coding: utf-8 -*-
"""GA4 (Property 313397200) 全历史只读分析：渠道/地域/品类/商品/系列/趋势。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

r = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GA4_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30)
at = r.json()["access_token"]
PROP = os.environ.get("GA4_PROPERTY_ID", "313397200")
URL = (f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}"
       f":runReport")
HDR = {"Authorization": f"Bearer {at}"}
FULL = {"startDate": "2020-01-01", "endDate": "2026-11-10"}
RECENT = {"startDate": "2026-08-13", "endDate": "2026-11-10"}


def rep(label, dims, mets, dr=FULL, order="sessions", limit=12, note=""):
    body = {"dateRanges": [dr],
            "dimensions": [{"name": d} for d in dims],
            "metrics": [{"name": m} for m in mets],
            "orderBys": [{"metric": {"metricName": order}, "desc": True}],
            "limit": limit}
    resp = httpx.post(URL, headers=HDR, json=body, timeout=60)
    print(f"\n===== {label} {note} =====")
    if resp.status_code != 200:
        print("[FAIL]", resp.status_code, resp.text[:200])
        return []
    rows = resp.json().get("rows", [])
    if not rows:
        print("(0 行)")
    for row in rows:
        d = [x["value"] for x in row.get("dimensionValues", [])] or ["总计"]
        m = [x["value"] for x in row["metricValues"]]
        print("  " + " | ".join(d) + " | " +
              " | ".join(f"{float(v):,.0f}" if float(v) > 99
                         else f"{float(v):,.2f}" for v in m))
    return rows


# 1. 全历史总盘
tot = rep("全历史总盘 (2020-01-01 ~ 2026-11-10)", [], 
          ["sessions", "totalUsers", "conversions", "purchaseRevenue",
           "itemsPurchased"], limit=1)

# 2. 近90天总盘（现在还活着吗）
rep("近90天总盘 (08-13 ~ 11-10)", [],
    ["sessions", "totalUsers", "conversions", "purchaseRevenue"],
    dr=RECENT, limit=1)

# 3. 月度趋势（有销售的月份）
rep("月度趋势", ["month"],
    ["sessions", "purchaseRevenue", "conversions"],
    order="purchaseRevenue", limit=15)

# 4. 渠道结构
rep("渠道结构", ["sessionDefaultChannelGroup"],
    ["sessions", "totalUsers", "conversions", "purchaseRevenue"])

# 5. 国家 top10
rep("国家/地区 top10", ["country"],
    ["sessions", "purchaseRevenue", "conversions"],
    order="purchaseRevenue")

# 6. 品类 top10
rep("商品品类 top10 (收入)", ["itemCategory"],
    ["purchaseRevenue", "itemsPurchased", "conversions"],
    order="purchaseRevenue")

# 7. 爆款单品 top15
rep("单品 top15 (收入)", ["itemName"],
    ["purchaseRevenue", "itemsPurchased"],
    order="purchaseRevenue", limit=15)

# 8. 历史广告系列（真实投过什么广告）
rep("广告系列 top12 (会话)", ["sessionCampaignName"],
    ["sessions", "conversions", "purchaseRevenue"],
    order="purchaseRevenue", limit=12)

# 9. 落地页 top10
rep("落地页 top10", ["landingPagePlusQueryString"],
    ["sessions", "purchaseRevenue", "conversions"],
    order="purchaseRevenue")
