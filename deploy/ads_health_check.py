# -*- coding: utf-8 -*-
"""两类广告全链路健康检查（只读，输出各层状态与异常清单）。"""
import os
from collections import Counter

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
SEARCH, PMAX = 24448362668, 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
issues = []


def rows(query):
    return list(gas.search(customer_id=CID, query=query))


print("=" * 60)
print("【1】Campaign 层（状态/投放/出价系统状态/预算/累计，排除历史REMOVED）")
for r in rows(
    "SELECT campaign.id, campaign.name, campaign.status, "
    "campaign.serving_status, campaign.bidding_strategy_system_status, "
    "campaign_budget.amount_micros, campaign_budget.explicitly_shared, "
    "metrics.impressions, metrics.clicks, metrics.cost_micros "
    "FROM campaign WHERE campaign.status != 'REMOVED' ORDER BY campaign.id"
):
    c, b, m = r.campaign, r.campaign_budget, r.metrics
    print(f"{c.name} | {c.status.name} | serving={c.serving_status.name} | "
          f"bidding={c.bidding_strategy_system_status.name} | "
          f"预算=¥{b.amount_micros/1e6:.0f}/天 shared={b.explicitly_shared} | "
          f"累计: 展示={m.impressions} 点击={m.clicks} 花费=¥{m.cost_micros/1e6:.2f}")
    if c.status.name != "ENABLED":
        issues.append(f"[{c.name}] 状态={c.status.name}")
    if c.serving_status.name != "SERVING":
        issues.append(f"[{c.name}] serving={c.serving_status.name}")

print("\n【2】Search 广告组状态")
for r in rows(
    "SELECT ad_group.name, ad_group.status FROM ad_group "
    f"WHERE campaign.id = {SEARCH}"
):
    print(f"  {r.ad_group.name} | {r.ad_group.status.name}")
    if r.ad_group.status.name != "ENABLED":
        issues.append(f"[Search组 {r.ad_group.name}] {r.ad_group.status.name}")

print("\n【3】Search 文字广告审批（关键：审核是否卡住/拒登）")
ads = rows(
    "SELECT ad_group_ad.status, ad_group_ad.policy_summary.approval_status, "
    "ad_group_ad.ad.type FROM ad_group_ad "
    f"WHERE campaign.id = {SEARCH}"
)
if not ads:
    print("  !! 无任何广告 —— 系列不可能投放")
    issues.append("[Search] 无文字广告")
for r in ads:
    a = r.ad_group_ad
    try:
        t = a.ad.type_.name
    except AttributeError:
        t = str(a.ad.type)
    print(f"  {t} | ad.status={a.status.name} | "
          f"审批={a.policy_summary.approval_status.name}")
    if a.status.name != "ENABLED":
        issues.append(f"[Search广告 {t}] status={a.status.name}")
    ap = a.policy_summary.approval_status.name
    if ap != "APPROVED":
        issues.append(f"[Search广告 {t}] 审批={ap}")

print("\n【4】Search 关键词投放状态分布（349 词）")
kw = rows(
    "SELECT ad_group_criterion.keyword.text, ad_group_criterion.status, "
    "ad_group_criterion.system_serving_status FROM ad_group_criterion "
    f"WHERE campaign.id = {SEARCH} AND ad_group_criterion.type = 'KEYWORD'"
)
dist = Counter(f"{r.ad_group_criterion.status.name}/"
               f"{r.ad_group_criterion.system_serving_status.name}" for r in kw)
print(f"  共 {len(kw)} 词")
for k, v in dist.most_common():
    print(f"  {k}: {v}")
    if not k.startswith("ENABLED/ELIGIBLE"):
        bad = [r.ad_group_criterion.keyword.text for r in kw
               if f"{r.ad_group_criterion.status.name}/"
               f"{r.ad_group_criterion.system_serving_status.name}" == k][:3]
        issues.append(f"[关键词 {k} 共{v}个] 例: {', '.join(bad)}")

print("\n【5】PMax asset_group 状态")
for r in rows(
    "SELECT asset_group.name, asset_group.status, asset_group.ad_strength "
    f"FROM asset_group WHERE campaign.id = {PMAX}"
):
    g = r.asset_group
    print(f"  {g.name} | {g.status.name} | ad_strength={g.ad_strength.name}")
    if g.status.name != "ENABLED":
        issues.append(f"[PMax组 {g.name}] {g.status.name}")

print("\n【6】PMax 素材状态（aga 层 + asset 层两段式）")
aga = rows(
    "SELECT asset_group_asset.field_type, asset_group_asset.status, "
    "asset_group_asset.asset FROM asset_group_asset "
    f"WHERE campaign.id = {PMAX}"
)
ft = Counter(a.asset_group_asset.field_type.name for a in aga)
print(f"  共 {len(aga)} 项:", dict(ft))
for r in aga:
    ag = r.asset_group_asset
    if ag.status.name != "ENABLED":
        issues.append(f"[PMax素材 {ag.resource_name}] aga={ag.status.name}")
        print(f"  aga异常: {ag.resource_name} | {ag.status.name}")
# asset 层审批状态（v26 无 asset.status，只查政策审批）
names = [r.asset_group_asset.asset for r in aga]
if names:
    in_list = ", ".join(f"'{n}'" for n in names)
    for r in rows(
        "SELECT asset.resource_name, asset.name, "
        "asset.policy_summary.approval_status FROM asset "
        f"WHERE asset.resource_name IN ({in_list})"
    ):
        a = r.asset
        ap = a.policy_summary.approval_status.name if a.policy_summary else "无政策项"
        if ap not in ("APPROVED", "无政策项"):
            issues.append(f"[PMax asset {a.name}] 审批={ap}")
            print(f"  asset异常: {a.name} | 审批={ap}")
print("  asset 层检查完成")

print("\n" + "=" * 60)
if issues:
    print(f"发现 {len(issues)} 项异常:")
    for i in issues:
        print(" -", i)
else:
    print("全部检查通过，无异常")
