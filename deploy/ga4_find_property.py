# -*- coding: utf-8 -*-
"""从 Google Ads 关联的 GA4 转化动作里挖 property_id。"""
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

q = (
    "SELECT conversion_action.id, conversion_action.name, "
    "conversion_action.google_analytics_4_settings.property_id "
    "FROM conversion_action "
    "WHERE conversion_action.id IN (947144115, 970409279)")
try:
    for r in gas.search(customer_id=CID, query=q):
        ca = r.conversion_action
        s = ca.google_analytics_4_settings
        print(f"#{ca.id} {ca.name}")
        print(f"  property_id = {s.property_id}")
except Exception as e:  # noqa: BLE001
    errs = list(getattr(e, "errors", []) or [])
    print("[FAIL]", (errs[0].message if errs else str(e))[:300])
