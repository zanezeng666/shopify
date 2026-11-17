# -*- coding: utf-8 -*-
"""统计 38 个暂停系列+Medical 的关键词匹配类型分布，确认 BROAD 改造量。只读。"""
import os
from collections import Counter

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

gac = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = gac.get_service("GoogleAdsService")

# 只统计相关系列（名称以 Estry 开头 = 38 暂停 + Medical）
stats = {}  # camp -> Counter(match_type)
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, ad_group_criterion.keyword.match_type, "
    "ad_group_criterion.criterion_id "
    "FROM ad_group_criterion "
    "WHERE campaign.name LIKE 'Estry%Search%' "
    "AND ad_group_criterion.type = 'KEYWORD'"))
tot = Counter()
for r in rows:
    mt = r.ad_group_criterion.keyword.match_type.name
    stats.setdefault(r.campaign.name, Counter())[mt] += 1
    tot[mt] += 1

for camp in sorted(stats):
    c = stats[camp]
    print(f"  {camp[:38]:<40} BROAD={c['BROAD']:>6} "
          f"PHRASE={c['PHRASE']:>5} EXACT={c['EXACT']:>5} "
          f"total={sum(c.values()):>6}")

print(f"\n合计: BROAD={tot['BROAD']} PHRASE={tot['PHRASE']} "
      f"EXACT={tot['EXACT']} 总词数={sum(tot.values())}")
