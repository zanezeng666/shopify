# -*- coding: utf-8 -*-
"""PMax Medical Estry 商品池空根因 v5：
A) 老 campaign(300552) 按日商品流量——feed 商品何时失去资格
B) 新 campaign(24441391608) shopping_setting 全量 + 近3天指标
C) 树节点 listing_source
"""
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


def gaql(q):
    return list(gas.search(customer_id=CID, query=q))


print("=" * 20, "A) 老 campaign 300552 按日商品流量", "=" * 20)
rows = gaql(
    "SELECT campaign.id, segments.date, metrics.clicks, "
    "metrics.impressions, metrics.cost_micros "
    "FROM shopping_performance_view "
    "WHERE campaign.id = 17652483274 AND segments.date DURING LAST_30_DAYS")
daily = {}
for r in rows:
    d = r.segments.date
    m = r.metrics
    e = daily.setdefault(d, [0, 0, 0.0])
    e[0] += m.clicks
    e[1] += m.impressions
    e[2] += m.cost_micros / 1e6
for d in sorted(daily):
    c, i, cost = daily[d]
    print(f"- {d}: imp={i} clicks={c} cost={cost:.2f}")

print("\n" + "=" * 20, "B) 新 campaign 配置与指标", "=" * 20)
rows = gaql(
    "SELECT campaign.name, campaign.status, "
    "campaign.shopping_setting.merchant_id, "
    "campaign.shopping_setting.feed_label, "
    "campaign.shopping_setting.campaign_priority, "
    "campaign.shopping_setting.enable_local "
    "FROM campaign WHERE campaign.id = 24441391608")
for r in rows:
    c = r.campaign
    ss = c.shopping_setting
    print(f"- {c.name!r} {c.status}")
    print(f"  merchant={ss.merchant_id} feed_label={ss.feed_label!r} "
          f"priority={ss.campaign_priority} local={ss.enable_local}")
rows = gaql(
    "SELECT campaign.id, campaign.name, metrics.clicks, "
    "metrics.impressions, metrics.cost_micros FROM campaign "
    "WHERE campaign.id = 24441391608")
for r in rows:
    m = r.metrics
    print(f"- 全期: imp={m.impressions} clicks={m.clicks} "
          f"cost={m.cost_micros/1e6:.2f}")

print("\n" + "=" * 20, "C) 树节点 listing_source", "=" * 20)
rows = gaql(
    "SELECT campaign.id, "
    "asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.listing_source "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608")
for r in rows:
    f = r.asset_group_listing_group_filter
    print(f"- id={f.id} {f.type_.name:<15} "
          f"source={f.listing_source.name if f.listing_source else '?'}")
