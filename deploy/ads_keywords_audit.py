# -*- coding: utf-8 -*-
"""拉 38 个 Search 系列的全部关键词词表+近7日花费，判定泛词/型号词。只读。"""
import os
import re

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

# 全量词表（不看指标）
kws = {}
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, ad_group.id, ad_group.name, "
    "ad_group_criterion.criterion_id, "
    "ad_group_criterion.keyword.text, "
    "ad_group_criterion.keyword.match_type, "
    "ad_group_criterion.status "
    "FROM ad_group_criterion "
    "WHERE campaign.advertising_channel_type = 'SEARCH' "
    "AND ad_group_criterion.type = 'KEYWORD'"))
for r in rows:
    kws[r.ad_group_criterion.criterion_id] = (
        r.campaign.name, r.ad_group.id, r.ad_group.name,
        r.ad_group_criterion.keyword.text,
        r.ad_group_criterion.keyword.match_type.name,
        r.ad_group_criterion.status.name)

# 近 7 日花费（按 criterion）
spend = {}
rows = gas.search(customer_id=CID, query=(
    "SELECT ad_group_criterion.criterion_id, metrics.cost_micros, "
    "metrics.clicks FROM keyword_view "
    "WHERE segments.date BETWEEN '2026-11-10' AND '2026-11-16'"))
for r in rows:
    spend[r.ad_group_criterion.criterion_id] = (
        r.metrics.cost_micros / 1e6, r.metrics.clicks)

# 泛词判定：无数字型号痕迹 = 泛词
GENERIC_BRAND = {
    "jbl", "sony", "philips", "panasonic", "dji", "psp", "ps", "xbox",
    "nintendo", "ipod", "apple", "samsung", "bosch", "dewalt", "makita",
    "bosch", "garmin", "corsair", "logitech", "razer", "husqvarna",
    "irobot", "roomba", "braava", "dyson", "shark", "retevis", "baofeng",
    "yeasu", "icome", "motorola", "hytera", "toshiba", "canon", "nikon"}


def is_generic(text: str) -> bool:
    t = text.lower()
    # 含字母+数字混合型号痕迹（如 m6, rt2, lb-75l, m3001a, fb2535c）= 型号词
    if re.search(r"[a-z]\d|\d[a-z]", t):
        return False
    # 纯数字电压容量（3.7v 2600mah）不算型号，但少见，保守算型号
    # 其余全算泛词
    return True


print(f"共 {len(kws)} 个关键词\n")
print(f"{'系列':<36} {'词':<34} {'匹配':<10} {'花费':>7} {'判':>4}")
n_model = n_generic = 0
for cid, (camp, agid, agname, text, mt, st) in sorted(
        kws.items(), key=lambda x: -spend.get(x[0], (0,))[0]):
    cost, clicks = spend.get(cid, (0.0, 0))
    gen = is_generic(text)
    n_generic += gen
    n_model += (not gen)
    print(f"  {camp[:34]:<36} {text[:32]:<34} {mt:<10} "
          f"${cost:<6.2f} {'泛' if gen else '型号'}")

print(f"\n型号词 {n_model} 个 / 泛词 {n_generic} 个")
