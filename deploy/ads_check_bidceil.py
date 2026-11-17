# -*- coding: utf-8 -*-
"""查 Search campaign 出价上限（只读，单位=CNY）。"""
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
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.bidding_strategy_type, "
    "campaign.target_spend.cpc_bid_ceiling_micros "
    "FROM campaign WHERE campaign.id IN (24441391608, 24448362668)"))
for r in rows:
    mc = r.campaign.target_spend
    ceil_ = mc.cpc_bid_ceiling_micros
    print(f"{r.campaign.name} | {r.campaign.bidding_strategy_type.name} "
          f"| cpc上限={ceil_/1e6 if ceil_ else '未设'} CNY")
