# -*- coding: utf-8 -*-
"""侦察4: dump 老PMax Medical系列的完整结构(campaign/budget/asset_group/
listing filters/assets) 作为建系列模板 + shopping_performance_view 试探MC。"""
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
OLD = "17557725557"   # PMax: Medical Battery


def gql(q, quiet=True):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/"
        "googleAds:searchStream", headers=H, json={"query": q}, timeout=30)
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for b in rows:
        if "error" in b:
            msg = b["error"]["details"][0]["errors"][0]["message"]
            if not quiet:
                print("  ERR:", msg[:120])
            continue
        out.extend(b.get("results", []))
    return out


# 1) campaign 全量字段 dump (shopping_setting 藏在里面)
rs = gql(
    "SELECT campaign.id, campaign.name, campaign.status, "
    "campaign.bidding_strategy_type, campaign.maximize_conversions, "
    "campaign.campaign_budget, campaign.advertising_channel_type, "
    "campaign.start_date, campaign.url_expansion_opt_out "
    f"FROM campaign WHERE campaign.id = {OLD}")
for e in rs:
    print("== campaign ==")
    print(json.dumps(e, ensure_ascii=False)[:900])

# 2) asset_group + listing filters
rs = gql(
    "SELECT asset_group.id, asset_group.name, asset_group.status, "
    "asset_group.final_urls, asset_group.campaign "
    f"FROM asset_group WHERE asset_group.campaign = "
    f"'customers/{CID}/campaigns/{OLD}'")
for e in rs:
    print("\n== asset_group ==")
    print(json.dumps(e, ensure_ascii=False)[:400])

rs = gql(
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.case_value, "
    "asset_group_listing_group_filter.parent_listing_group_filter, "
    "asset_group_listing_group_filter.asset_group "
    "FROM asset_group_listing_group_filter "
    f"WHERE asset_group.campaign = 'customers/{CID}/campaigns/{OLD}'")
for e in rs:
    f = e["assetGroupListingGroupFilter"]
    print("\n== listing_filter ==")
    print(json.dumps(f, ensure_ascii=False)[:500])

# 3) asset_group_asset (素材形状模板)
rs = gql(
    "SELECT asset_group_asset.asset, asset_group_asset.field_type, "
    "asset_group_asset.status "
    "FROM asset_group_asset "
    f"WHERE asset_group.campaign = 'customers/{CID}/campaigns/{OLD}'")
kinds = {}
for e in rs:
    ft = e["assetGroupAsset"]["fieldType"]
    kinds[ft] = kinds.get(ft, 0) + 1
print("\n== 素材类型统计 ==", kinds)

# 4) shopping_performance_view 试探 (报错可能带MC信息)
rs = gql(
    "SELECT segments.product_item_id, metrics.clicks, metrics.cost_micros "
    "FROM shopping_performance_view "
    "WHERE segments.date BETWEEN '2026-11-01' AND '2026-11-08'", quiet=False)
print(f"\n== shopping_perf_view 行数: {len(rs)}")
for e in rs[:3]:
    print(" ", json.dumps(e, ensure_ascii=False)[:200])
