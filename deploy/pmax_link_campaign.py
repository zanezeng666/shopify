# -*- coding: utf-8 -*-
"""BUSINESS_NAME + LOGO 挂到 campaign 级（Brand Guidelines 要求）。"""
import os

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
CAMP = f"customers/{CID}/campaigns/24441391608"

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

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json",
     "developer-token": "unused"}
for asset, ft in ((bn, "BUSINESS_NAME"), (logo, "LOGO")):
    r = httpx.post(
        f"https://googleads.googleapis.com/v26/customers/{CID}"
        "/campaignAssets:mutate", headers=H,
        json={"operations": [{"create": {
            "campaign": CAMP, "asset": asset, "fieldType": ft}}]},
        timeout=120)
    ok = r.status_code == 200
    if not ok:
        errs = r.json().get("error", {}).get("details", [])
        for e in errs:
            for er in e.get("errors", []):
                print(ft, "ERR:", er.get("errorCode"), "|",
                      er.get("message", "")[:200])
    print(f"{ft}: {r.status_code}")
