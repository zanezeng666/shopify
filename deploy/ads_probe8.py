# -*- coding: utf-8 -*-
"""侦察8: 老PMax的BUSINESS_NAME asset真实形状。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}",
     "Content-Type": "application/json", "developer-token": "unused"}
CID = "7059800494"


def gql(q):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/"
        "googleAds:searchStream", headers=H, json={"query": q}, timeout=30)
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for b in rows:
        if "error" in b:
            print("ERR:", b["error"]["details"][0]["errors"][0]
                  ["message"][:140])
        else:
            out.extend(b.get("results", []))
    return out


rs = gql(
    "SELECT asset_group_asset.asset FROM asset_group_asset "
    "WHERE asset_group_asset.asset_group = "
    f"'customers/{CID}/assetGroups/6446984775' "
    "AND asset_group_asset.field_type = 'BUSINESS_NAME'")
if not rs:
    print("老系列无 BUSINESS_NAME asset")
else:
    arn = rs[0]["assetGroupAsset"]["asset"]
    print("biz asset:", arn)
    for q2 in (
        f"SELECT asset.name, asset.text_asset.text "
        f"FROM asset WHERE asset.resource_name = '{arn}'",
        f"SELECT asset.name FROM asset WHERE asset.resource_name = '{arn}'",
    ):
        rs2 = gql(q2)
        if rs2:
            print("字段OK:", rs2[0])
            break
