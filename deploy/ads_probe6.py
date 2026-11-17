# -*- coding: utf-8 -*-
"""侦察6: shopping_setting.* 通配试探 + 老系列listing filter模板完整打印。"""
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


def run(q):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/"
        "googleAds:searchStream", headers=H, json={"query": q}, timeout=30)
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    for b in rows:
        if "error" in b:
            print("ERR:", b["error"]["details"][0]["errors"][0]
                  ["message"][:150])
            return
        for e in b.get("results", []):
            print(json.dumps(e, ensure_ascii=False)[:600])


print("== 1) shopping_setting.* 通配 ==")
run(f"SELECT campaign.shopping_setting.* FROM campaign "
    f"WHERE campaign.id = {OLD}")

print("\n== 2) 老系列 listing filter 模板 ==")
run("SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.case_value, "
    "asset_group_listing_group_filter.parent_listing_group_filter "
    "FROM asset_group_listing_group_filter "
    f"WHERE asset_group.campaign = 'customers/{CID}/campaigns/{OLD}'")

print("\n== 3) 老系列 asset_group_asset 素材样本(标题/描述文案参考) ==")
run("SELECT asset.text_asset.text, asset_group_asset.field_type "
    "FROM asset_group_asset, asset "
    "WHERE asset_group_asset.asset = asset.resource_name "
    f"AND asset_group_asset.asset_group = "
    f"'customers/{CID}/assetGroups/6446984775' "
    "AND asset_group_asset.field_type IN ('HEADLINE', 'LONG_HEADLINE', "
    "'DESCRIPTION', 'BUSINESS_NAME')")
