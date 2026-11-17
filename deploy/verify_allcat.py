# -*- coding: utf-8 -*-
"""全量验证：38 分类搜索广告结构/预算/状态/政策/资产完整性 -> 最终报告。"""
import json

from ads_create_allcat_search import q  # noqa

plans = json.load(open("/tmp/allcat_plans.json"))
want = {p["campaign"] for p in plans}

# 1) campaign 层：状态/预算/出价策略
camps = {}
for r in q(
        "SELECT campaign.name, campaign.status, "
        "campaign_budget.amount_micros, "
        "bidding_strategy.name "
        "FROM campaign WHERE campaign.status != 'REMOVED' "
        "AND campaign.advertising_channel_type = 'SEARCH'"):
    c = r["campaign"]
    b = r.get("campaignBudget") or {}
    s = r.get("biddingStrategy") or {}
    camps[c["name"]] = {
        "status": c["status"], "budget": b.get("amountMicros"),
        "strategy": s.get("name")}

new = {k: v for k, v in camps.items() if k in want}
old = {k: v for k, v in camps.items() if k not in want}
print(f"=== 目标 campaign: 计划{len(want)} 实建{len(new)} "
      f"缺{len(want - set(new))}")
for m in sorted(want - set(new)):
    print("  MISSING:", m)
bad = [k for k, v in new.items()
       if v["status"] != "ENABLED" or v["budget"] != "50000000"]
print("非ENABLED或预算≠¥50:", bad or "无")
tot_cny = sum(int(v["budget"]) for v in new.values()) / 1_000_000
print(f"新增总预算: ¥{tot_cny:.0f}/天 | 既有(含Medical):",
      {k: f"¥{int(v['budget']) / 1e6:.0f}" for k, v in old.items()})

# 2) ad group / keyword / RSA 完整性
agc, kwc, adsc = {}, {}, {}
for r in q("SELECT campaign.name FROM ad_group "
           "WHERE ad_group.status != 'REMOVED' "
           "AND campaign.status != 'REMOVED'"):
    n = r["campaign"]["name"]
    agc[n] = agc.get(n, 0) + 1
for r in q("SELECT campaign.name FROM ad_group_criterion "
           "WHERE ad_group_criterion.status != 'REMOVED' "
           "AND ad_group_criterion.type = 'KEYWORD' "
           "AND campaign.status != 'REMOVED'"):
    n = r["campaign"]["name"]
    kwc[n] = kwc.get(n, 0) + 1
pol_stat = {}
for r in q("SELECT campaign.name, ad_group_ad.policy_summary.approval_status "
           "FROM ad_group_ad WHERE ad_group_ad.status != 'REMOVED' "
           "AND campaign.status != 'REMOVED'"):
    n = r["campaign"]["name"]
    adsc[n] = adsc.get(n, 0) + 1
    a = ((r.get("adGroupAd") or {}).get("policySummary") or {}
         ).get("approvalStatus")
    if a:
        pol_stat[(n, a)] = pol_stat.get((n, a), 0) + 1

print("\n=== 结构核对（组/词/RSA）")
short = []
for p in plans:
    n = p["campaign"]
    wa = len(p["ad_groups"])
    wk = sum(len(g["keywords"]) for g in p["ad_groups"])
    row = (n, f"{agc.get(n, 0)}/{wa}组", f"{kwc.get(n, 0)}词",
           f"{adsc.get(n, 0)}RSA")
    flag = "" if agc.get(n, 0) == wa and adsc.get(n, 0) == wa else "  <<<"
    print(f"  {n:44} {row[1]:>8} {row[2]:>6} {row[3]:>5}{flag}")
    if flag:
        short.append(n)

print("\n=== 广告政策状态")
from collections import Counter  # noqa: E402
agg = Counter()
for (n, a), c in pol_stat.items():
    agg[a] += c
print("  全账户 SEARCH 广告审批分布:", dict(agg) or "无数据")
for (n, a), c in sorted(pol_stat.items()):
    if a != "APPROVED":
        print(f"  {n}: {a} x{c}")

# 3) 负词组/callout 挂载
ss = set()
for r in q("SELECT campaign_shared_set.campaign, "
           "campaign_shared_set.shared_set FROM campaign_shared_set"):
    ss.add(r["campaignSharedSet"]["campaign"].rsplit("/", 1)[-1])
ca = set()
for r in q("SELECT campaign_asset.campaign FROM campaign_asset "
           "WHERE campaign_asset.field_type = 'CALLOUT'"):
    ca.add(r["campaignAsset"]["campaign"].rsplit("/", 1)[-1])
# campaign id -> name 反查
id2n = {}
for r in q("SELECT campaign.id, campaign.name FROM campaign "
           "WHERE campaign.status != 'REMOVED'"):
    id2n[r["campaign"]["id"]] = r["campaign"]["name"]
miss_ss = [id2n[i] for i in ss if id2n.get(i) in want]
have_ss_n = sum(1 for i in ss if id2n.get(i) in want)
have_ca_n = sum(1 for i in ca if id2n.get(i) in want)
print(f"\n=== 挂载: 负词组 {have_ss_n}/{len(want)} | callout {have_ca_n}/{len(want)}")
print("\n验证完成")
