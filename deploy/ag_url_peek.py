# -*- coding: utf-8 -*-
"""查 PMax 素材资源组的网址选项字段现状 + 系列级网址扩展设置"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": CID,
    "use_proto_plus": True,
})
gac = ads.get_service("GoogleAdsService")

print("=== asset_group 网址字段 ===")
q = ("SELECT asset_group.id, asset_group.name, asset_group.final_urls, "
     "asset_group.path1, asset_group.path2, asset_group.campaign "
     "FROM asset_group WHERE campaign.id = 24441391608")
for row in gac.search(customer_id=CID, query=q):
    ag = row.asset_group
    print(f"  组: {ag.name} ({ag.id})")
    print(f"  final_urls: {list(ag.final_urls) or '(空)'}")
    print(f"  path1: '{ag.path1}'  path2: '{ag.path2}'")

print("\n=== 系列级 网址扩展/跟踪 ===")
q2 = ("SELECT campaign.name, campaign.tracking_url_template, "
      "campaign.final_url_suffix "
      "FROM campaign WHERE campaign.id = 24441391608")
for row in gac.search(customer_id=CID, query=q2):
    c = row.campaign
    print(f"  campaign: {c.name}")
    print(f"  tracking_url_template: '{c.tracking_url_template}'")
    print(f"  final_url_suffix: '{c.final_url_suffix}'")
