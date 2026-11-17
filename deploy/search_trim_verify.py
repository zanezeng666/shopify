# -*- coding: utf-8 -*-
"""Search 收缩三确认：CPC 封顶 ¥1.5 / 否定词集关联数 / ENABLED 系列与预算。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# 1) CPC 封顶
rows = gas.search(customer_id=CID, query=(
    "SELECT bidding_strategy.id, bidding_strategy.name, "
    "bidding_strategy.target_spend.cpc_bid_ceiling_micros "
    "FROM bidding_strategy"))
print("== CPC 封顶 ==")
for r in rows:
    b = r.bidding_strategy
    print(f"  {b.name[:36]:<36} ¥{b.target_spend.cpc_bid_ceiling_micros/1e6:.2f}")

# 2) 否定词集关联
rows = gas.search(customer_id=CID, query=(
    "SELECT shared_set.name, shared_set.type, shared_set.id "
    "FROM shared_set"))
sst = None
for r in rows:
    if "estry_nav_junk" in r.shared_set.name:
        sst = r.shared_set.id
        print(f"\n== 否定词集 ==\n  {r.shared_set.name} id={sst}")
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign_shared_set.campaign FROM campaign_shared_set "
    f"WHERE shared_set.id = {sst}"))
print(f"  关联系列数: {len(list(rows))}")

# 3) ENABLED 系列数（预算零增量=维持现状，仅清点）
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.advertising_channel_type FROM campaign "
    "WHERE campaign.status = 'ENABLED'"))
from collections import Counter
c = Counter(r.campaign.advertising_channel_type.name for r in rows)
print("\n== ENABLED 系列清点 ==")
for t, n in c.items():
    print(f"  {t}: {n}")
