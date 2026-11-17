# -*- coding: utf-8 -*-
"""取 PMax asset group 的 final_urls（拿店铺域名）。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id="7059800494", query=(
    "SELECT asset_group.final_urls FROM asset_group "
    "WHERE campaign.status='ENABLED'"))
for r in rows:
    print(r.asset_group.final_urls)
