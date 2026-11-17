# -*- coding: utf-8 -*-
"""确认账户级 auto-tagging 状态"""
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
q = "SELECT customer.auto_tagging_enabled FROM customer"
for row in gac.search(customer_id=CID, query=q):
    print(f"auto_tagging_enabled: {row.customer.auto_tagging_enabled}")
