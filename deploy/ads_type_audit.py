# -*- coding: utf-8 -*-
"""只读审计：各广告类型近 30 天消耗/产出 + PMax 素材 + 账户预算。"""
import os
from collections import defaultdict

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# 1) 近 30 天按广告类型聚合
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.advertising_channel_type, campaign.status, "
    "metrics.cost_micros, metrics.clicks, metrics.impressions, "
    "metrics.conversions, metrics.ctr, metrics.average_cpc "
    "FROM campaign WHERE segments.date BETWEEN '2026-10-17' "
    "AND '2026-11-15'"))
agg = defaultdict(lambda: [0.0, 0, 0, 0.0, 0])  # cost, clicks, imps, conv, n
for r in rows:
    a = agg[r.campaign.advertising_channel_type.name]
    a[0] += r.metrics.cost_micros / 1e6
    a[1] += r.metrics.clicks
    a[2] += r.metrics.impressions
    a[3] += r.metrics.conversions
    a[4] += 1
print("=== 近 30 天按广告类型（含已停系列）===")
for t, (c, k, i, v, n) in sorted(agg.items(), key=lambda x: -x[1][0]):
    print(f"{t:<12} ${c:>7.2f}  clicks={k:<5} imps={i:<7} conv={v:<4.0f} "
          f"series_rows={n}  cpc=${(c / k if k else 0):.2f}")

# 2) PMax asset group 素材现状
rows2 = gas.search(customer_id=CID, query=(
    "SELECT asset_group.name, asset_group.status, "
    "asset_group.ad_strength, campaign.name "
    "FROM asset_group WHERE campaign.status = 'ENABLED'"))
print("\n=== PMax asset groups ===")
for r in rows2:
    print(f"  {r.asset_group.name:<30} {r.asset_group.status.name:<8} "
          f"strength={r.asset_group.ad_strength.name}")

# 3) 账户预算分布
rows3 = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, campaign.daily_budget.amount_micros, "
    "campaign.advertising_channel_type, campaign.status "
    "FROM campaign WHERE campaign.status = 'ENABLED' "
    "AND campaign.daily_budget.amount_micros > 0"))
print("\n=== ENABLED 系列预算 ===")
for r in rows3:
    c = r.campaign
    print(f"  [{c.advertising_channel_type.name[:8]:<8}] "
          f"${c.daily_budget.amount_micros / 1e6:>5.2f}/天  {c.name[:40]}")

# 4) MC 免费 listing 线索：PMax 商品资源分布（购物列表额）
rows4 = gas.search(customer_id=CID, query=(
    "SELECT asset_group_listing_group_filter.type "
    "FROM asset_group_listing_group_filter"))
print(f"\nlisting_group_filters: {len(list(rows4))} 个节点")
