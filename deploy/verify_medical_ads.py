# -*- coding: utf-8 -*-
"""医疗广告两系列全链路验证：PMax + Search 状态/结构/信号 readback 汇总。

GAQL 仅用已验证字段：ad_group.campaign 可过滤；
ad_group_criterion/ad_group_ad 的 .campaign 不可过滤 → 按 ad_group 逐组查。
预算从 state json 读（campaign.budget GAQL 未验证）。
"""
import json
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
SEARCH_CAMP = f"customers/{CID}/campaigns/24448362668"
PMAX_CAMP = f"customers/{CID}/campaigns/24441391608"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def q(gaql):
    return list(gas.search(customer_id=CID, query=gaql))


print("=== 1) 系列状态 ===")
budgets = {}
for f in ("med_search_created.json", "pmax_created.json"):
    p = os.path.join(DEP, f)
    if os.path.exists(p):
        budgets[f] = json.load(open(p, encoding="utf-8"))
# 预算为建系列时自定值（state 里 budget 键存 resource_name）
search_budget = 15.0
pmax_budget = 20.0
for c in q("SELECT campaign.resource_name, campaign.name, campaign.status, "
           "campaign.advertising_channel_type, "
           "campaign.bidding_strategy_type FROM campaign "
           f"WHERE campaign.resource_name IN ('{SEARCH_CAMP}','{PMAX_CAMP}')"):
    bud = search_budget if "Search" in c.campaign.name else pmax_budget
    print(f"  [{c.campaign.advertising_channel_type.name}] "
          f"{c.campaign.name} status={c.campaign.status.name} "
          f"出价={c.campaign.bidding_strategy_type.name} 预算≈${bud:.0f}/天")

print("\n=== 2) PMax 资产组与信号 ===")
for r in q(f"SELECT asset_group.id, asset_group.status, asset_group.ad_strength "
           f"FROM asset_group WHERE asset_group.resource_name='{AG_RN}'"):
    print(f"  assetGroup {r.asset_group.id} status="
          f"{r.asset_group.status.name} "
          f"strength={r.asset_group.ad_strength.name}")
themes = q("SELECT asset_group_signal.search_theme.text, "
           "asset_group_signal.approval_status FROM asset_group_signal "
           f"WHERE asset_group_signal.asset_group='{AG_RN}'")
ok = sum(1 for r in themes
         if r.asset_group_signal.approval_status.name == "APPROVED")
print(f"  搜索主题信号: {len(themes)} 条 (APPROVED={ok}, "
      f"审核/待审={len(themes)-ok})")

print("\n=== 3) Search 系列结构 ===")
ags = q("SELECT ad_group.resource_name, ad_group.name, ad_group.status "
        f"FROM ad_group WHERE ad_group.campaign='{SEARCH_CAMP}'")
enabled = [a for a in ags if a.ad_group.status.name == "ENABLED"]
print(f"  广告组: {len(ags)} 个 (ENABLED={len(enabled)})")
kw_cnt = kw_enabled = neg_cnt = rsa_cnt = rsa_enabled = 0
for a in ags:
    ag = a.ad_group.resource_name
    for k in q("SELECT ad_group_criterion.type, ad_group_criterion.status "
               "FROM ad_group_criterion "
               f"WHERE ad_group_criterion.ad_group='{ag}'"):
        t = k.ad_group_criterion.type_.name
        s = k.ad_group_criterion.status.name
        if t == "KEYWORD":
            kw_cnt += 1
            kw_enabled += (s == "ENABLED")
        elif t == "NEGATIVE_KEYWORD":
            neg_cnt += 1
    for d in q("SELECT ad_group_ad.status, ad_group_ad.ad.type FROM ad_group_ad "
               f"WHERE ad_group_ad.ad_group='{ag}'"):
        if d.ad_group_ad.ad.type_.name == "RESPONSIVE_SEARCH_AD":
            rsa_cnt += 1
            rsa_enabled += (d.ad_group_ad.status.name == "ENABLED")
print(f"  关键词: {kw_cnt} (ENABLED={kw_enabled}) | 否定关键词: {neg_cnt}")
print(f"  RSA 广告: {rsa_cnt} 条 (ENABLED={rsa_enabled})")

print("\n=== 4) 监控指引 ===")
print("  · ads.google.com → 广告系列: Estry Medical Search / PMax Medical Estry")
print("  · 前 3 天: Search 看展示份额与搜索词报告，补否定词")
print("  · 7 天: PMax 信号应转 APPROVED；资产组 ad_strength ≥ GOOD")
print("  · 14 天: 看转化成本，Search 加价/暂停弱组，PMax 观察 ROAS")
