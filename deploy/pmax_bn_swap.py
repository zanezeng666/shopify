# -*- coding: utf-8 -*-
"""查 campaign 级现有 asset（BUSINESS_NAME 占位者）→ remove 旧的 → 挂新的。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
CAMP_ID = "24441391608"
CAMP = f"customers/{CID}/campaigns/{CAMP_ID}"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    f"SELECT campaign.id, campaign_asset.resource_name, "
    "campaign_asset.field_type, "
    "asset.text_asset.text FROM campaign_asset "
    f"WHERE campaign.id = {CAMP_ID}"))
old = None
for r in rows:
    print(r.campaign_asset.field_type.name, "|",
          r.asset.text_asset.text or "(non-text)", "|",
          r.campaign_asset.resource_name)
    if r.campaign_asset.field_type.name == "BUSINESS_NAME":
        old = r.campaign_asset.resource_name

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json",
     "developer-token": "unused"}

if old:
    rr = httpx.post(
        f"https://googleads.googleapis.com/v26/customers/{CID}"
        "/campaignAssets:mutate", headers=H,
        json={"operations": [{"remove": old}]}, timeout=60)
    print("remove old BUSINESS_NAME:", rr.status_code,
          "" if rr.status_code == 200 else rr.text[:200])

bn = [r.asset.resource_name for r in gas.search(customer_id=CID, query=(
    "SELECT asset.resource_name FROM asset "
    "WHERE asset.text_asset.text = 'EstryBattery'"))][0]
rc = httpx.post(
    f"https://googleads.googleapis.com/v26/customers/{CID}"
    "/campaignAssets:mutate", headers=H,
    json={"operations": [{"create": {
        "campaign": CAMP, "asset": bn,
        "fieldType": "BUSINESS_NAME"}}]}, timeout=60)
print("create EstryBattery BUSINESS_NAME:", rc.status_code,
      "" if rc.status_code == 200 else rc.text[:300])
