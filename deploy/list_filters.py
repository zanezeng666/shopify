# -*- coding: utf-8 -*-
"""查账号内所有 asset_group_listing_group_filter 节点结构 (抄老 PMax 的作业)."""
import httpx
import json
import os

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"


def token():
    return httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


q = ("SELECT asset_group_listing_group_filter.resource_name, "
     "asset_group_listing_group_filter.type, "
     "asset_group_listing_group_filter.parent_listing_group_filter, "
     "asset_group_listing_group_filter.listing_source "
     "FROM asset_group_listing_group_filter")
r = httpx.post(f"{API}/googleAds:searchStream",
               headers={"Content-Type": "application/json",
                        "developer-token": "unused",
                        "Authorization": f"Bearer {token()}"},
               json={"query": q}, timeout=60)
print("HTTP", r.status_code, r.text[:800])
for arr in r.json():
    for row in arr.get("results", []):
        f = row["assetGroupListingGroupFilter"]
        print(json.dumps(f, ensure_ascii=False))
