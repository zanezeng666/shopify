# -*- coding: utf-8 -*-
"""重试 LOGO / BUSINESS_NAME 挂载，打印完整错误。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")
logo = [r.asset.resource_name for r in gas.search(customer_id=CID, query=(
    "SELECT asset.resource_name FROM asset "
    "WHERE asset.name = 'Estry Logo Square'"))][0]
bn = [r.asset.resource_name for r in gas.search(customer_id=CID, query=(
    "SELECT asset.resource_name FROM asset "
    "WHERE asset.text_asset.text = 'EstryBattery'"))][0]
print("logo:", logo, "\nbn:", bn)

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json",
     "developer-token": "unused"}
for asset, ft in ((logo, "LOGO"), (bn, "BUSINESS_NAME")):
    r2 = httpx.post(
        f"https://googleads.googleapis.com/v26/customers/{CID}"
        "/assetGroupAssets:mutate", headers=H,
        json={"operations": [{"create": {
            "assetGroup": AG, "asset": asset, "fieldType": ft}}]},
        timeout=120)
    print(f"\n=== {ft} {r2.status_code} ===")
    print(r2.text[:1000])
