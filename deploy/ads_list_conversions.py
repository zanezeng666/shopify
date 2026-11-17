# -*- coding: utf-8 -*-
"""诊断：列出账户全部转化操作（只读）。"""
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

rows = list(gas.search(customer_id=CID, query=(
    "SELECT conversion_action.id, conversion_action.name, "
    "conversion_action.status, conversion_action.category, "
    "conversion_action.primary_for_goal "
    "FROM conversion_action")))
if not rows:
    print("账户 0 个转化操作 —— PMax 出价策略无目标可用，与后台提示一致")
for r in rows:
    ca = r.conversion_action
    print(f"#{ca.id} {ca.name} | {ca.category.name} | {ca.status.name} "
          f"| primary_for_goal={ca.primary_for_goal}")
