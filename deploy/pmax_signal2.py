# -*- coding: utf-8 -*-
"""PMax asset_group 挂 GA4 受众信号 (audiences/364029771)"""
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")
CAMP = "24441391608"
AG = "6770847164"

from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": CID,
    "use_proto_plus": True,
})
ags = ads.get_service("AssetGroupSignalService")
sig = ads.get_type("AssetGroupSignal")
sig.asset_group = f"customers/{CID}/assetGroups/{AG}"
sig.audience.audience = f"customers/{CID}/audiences/364029771"
op = ads.get_type("AssetGroupSignalOperation")
op.create = sig
r = ags.mutate_asset_group_signals(customer_id=CID, operations=[op])
print(f"GA4 受众信号已挂: {r.results[0].resource_name}")
