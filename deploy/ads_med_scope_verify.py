# -*- coding: utf-8 -*-
"""收敛后健康检查：campaign/asset group 状态 + 终态树确认。"""
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

q_camp = (
    "SELECT campaign.name, campaign.status, campaign.serving_status "
    "FROM campaign WHERE campaign.id IN (24441391608, 24448362668)")
print("=== 广告系列状态 ===")
for r in gas.search(customer_id=CID, query=q_camp):
    c = r.campaign
    print(f"  {c.name} | status={c.status.name} serving={c.serving_status.name}")

q_ag = (
    "SELECT asset_group.id, asset_group.status, "
    "asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_type.level "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608")
print("=== PMax 资产组与商品组树 ===")
for r in gas.search(customer_id=CID, query=q_ag):
    f = r.asset_group_listing_group_filter
    ag = r.asset_group
    print(f"  asset_group={ag.id}({ag.status.name}) node={f.id} "
          f"type={f.type_.name} "
          f"ptype={f.case_value.product_type.value or '(else)'} "
          f"level={f.case_value.product_type.level.name}")
