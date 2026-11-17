# -*- coding: utf-8 -*-
"""shopping_performance_view 查询逐步拆解定位。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

tests = [
    ("A 仅offer_id+日期",
     "SELECT shopping_performance_view.offer_id "
     "FROM shopping_performance_view "
     "WHERE segments.date BETWEEN '2026-11-01' AND '2026-11-12'"),
    ("B +campaign过滤",
     "SELECT shopping_performance_view.offer_id "
     "FROM shopping_performance_view "
     f"WHERE campaign.id = {PMAX} "
     "AND segments.date BETWEEN '2026-11-01' AND '2026-11-12'"),
    ("C +imp过滤+metrics",
     "SELECT shopping_performance_view.offer_id, "
     "metrics.impressions, metrics.clicks "
     "FROM shopping_performance_view "
     f"WHERE campaign.id = {PMAX} AND metrics.impressions > 0 "
     "AND segments.date BETWEEN '2026-11-01' AND '2026-11-12'"),
]
for label, q in tests:
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"✓ {label}: {len(rs)} 行")
        if rs:
            print(f"   样本 offer: "
                  f"{rs[0].shopping_performance_view.offer_id[:46]}")
    except Exception as e:  # noqa: BLE001
        s = str(e)
        i = s.find("errors {")
        print(f"✗ {label}: {s[i:i+260] if i >= 0 else s[:160]}")
