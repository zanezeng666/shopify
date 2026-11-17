# -*- coding: utf-8 -*-
"""Search 系列实际 CPC 与丢失份额（只读，单位=CNY）。"""
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

print("=== Search 系列累计（账户货币 CNY） ===")
rows = list(gas.search(customer_id=CID, query=(
    "SELECT campaign.name, metrics.impressions, metrics.clicks, "
    "metrics.cost_micros, metrics.average_cpc, metrics.ctr, "
    "metrics.search_budget_lost_impression_share, "
    "metrics.search_rank_lost_impression_share "
    "FROM campaign WHERE campaign.id = 24448362668")))
for r in rows:
    m = r.metrics
    print(f"展示={m.impressions} 点击={m.clicks} "
          f"花费=¥{m.cost_micros/1e6:.2f} 实际均CPC=¥{m.average_cpc/1e6:.2f} "
          f"CTR={m.ctr:.2f}%")
    blis = m.search_budget_lost_impression_share
    rlis = m.search_rank_lost_impression_share
    print(f"预算受限丢失份额={blis:.2f} 排名不足丢失份额={rlis:.2f}"
          if blis is not None and rlis is not None else "")

print("\n=== 花费 Top 10 关键词（实际单价） ===")
rows = list(gas.search(customer_id=CID, query=(
    "SELECT ad_group_criterion.keyword.text, metrics.impressions, "
    "metrics.clicks, metrics.cost_micros, metrics.average_cpc "
    "FROM keyword_view WHERE campaign.id = 24448362668 "
    "ORDER BY metrics.cost_micros DESC LIMIT 10")))
for r in rows:
    m = r.metrics
    print(f"{r.ad_group_criterion.keyword.text:32s} "
          f"展示={m.impressions:4d} 点击={m.clicks:3d} "
          f"花费=¥{m.cost_micros/1e6:.2f} 均CPC=¥{m.average_cpc/1e6:.2f}")
