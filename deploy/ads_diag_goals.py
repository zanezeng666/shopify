# -*- coding: utf-8 -*-
"""诊断：PMax campaign 目标配置 + 账户级转化目标开关（只读）。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = f"customers/{CID}/campaigns/24441391608"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

print("=== PMax campaign 级目标 ===")
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign_conversion_goal.category "
    "FROM campaign_conversion_goal "
    f"WHERE campaign_conversion_goal.campaign = '{PMAX}'"))
for r in rows:
    print(r.campaign_conversion_goal.category.name)

print("\n=== 账户级 category 目标开关（biddable=可出价优化） ===")
rows = gas.search(customer_id=CID, query=(
    "SELECT customer_conversion_goal.category, "
    "customer_conversion_goal.biddable "
    "FROM customer_conversion_goal"))
for r in rows:
    g = r.customer_conversion_goal
    print(f"{g.category.name} | biddable={g.biddable}")
