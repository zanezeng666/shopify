# -*- coding: utf-8 -*-
"""探 BrandGuidelines 消息结构 + 查当前值。"""
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
bg = client.get_type("Campaign").brand_guidelines._pb.DESCRIPTOR.fields_by_name
print("BrandGuidelines 字段:")
for k, v in bg.items():
    print(f"  {k} ({v.message_type.full_name if v.message_type else v.type})")

gas = client.get_service("GoogleAdsService")
try:
    q = ("SELECT campaign.brand_guidelines_enabled, "
         "campaign.brand_guidelines.business_name "
         "FROM campaign WHERE campaign.id = 24441391608")
    for r in gas.search(customer_id=CID, query=q):
        print(f"\nbrand_guidelines_enabled = {r.campaign.brand_guidelines_enabled}")
        print(f"business_name = {r.campaign.brand_guidelines.business_name or '(空)'}")
except Exception as e:  # noqa: BLE001
    try:
        print("查询失败:", e.failure.errors[0].message[:250])
    except Exception:  # noqa: BLE001
        print("查询失败:", str(e)[:250])
