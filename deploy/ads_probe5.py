# -*- coding: utf-8 -*-
"""侦察5: SELECT campaign 整资源取 shopping_setting.merchant_center_id。"""
import json
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
OLD = "17557725557"

r = httpx.post(
    f"https://googleads.googleapis.com/v25/customers/{CID}/"
    "googleAds:searchStream", headers=H,
    json={"query": f"SELECT campaign FROM campaign "
                   f"WHERE campaign.id = {OLD}"}, timeout=30)
rows = r.json() if isinstance(r.json(), list) else [r.json()]
for b in rows:
    if "error" in b:
        print("ERR:", b["error"]["details"][0]["errors"][0]["message"][:200])
        continue
    for e in b.get("results", []):
        c = e["campaign"]
        print("name:", c.get("name"))
        print("status:", c.get("status"))
        print("shoppingSetting:", json.dumps(
            c.get("shoppingSetting"), ensure_ascii=False))
        print("biddingStrategy:", c.get("biddingStrategyType"),
              "maxConv:", bool(c.get("maximizeConversions")))
        print("budget:", c.get("campaignBudget"))
        print("urlExpansionOptOut:", c.get("urlExpansionOptOut"))

# listing filter 完整结构 (建系列模板)
r2 = httpx.post(
    f"https://googleads.googleapis.com/v25/customers/{CID}/"
    "googleAds:searchStream", headers=H,
    json={"query": "SELECT asset_group_listing_group_filter FROM "
                   "asset_group_listing_group_filter WHERE "
                   f"asset_group.campaign = 'customers/{CID}/campaigns/"
                   f"{OLD}'"}, timeout=30)
rows2 = r2.json() if isinstance(r2.json(), list) else [r2.json()]
print("\n== listing filters ==")
for b in rows2:
    if "error" in b:
        print("ERR:", b["error"]["details"][0]["errors"][0]["message"][:200])
        continue
    for e in b.get("results", []):
        print(json.dumps(e["assetGroupListingGroupFilter"],
                         ensure_ascii=False)[:400])
