# -*- coding: utf-8 -*-
"""诊断层3：asset_group_ad 审批状态 + 政策细节。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def rows(q, label=""):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        return rs
    except Exception as e:  # noqa: BLE001
        errs = getattr(e, "errors", [])
        msg = errs[0].message[:200] if errs else str(e)[:200]
        print(f"  [查询失败:{label}] {msg}")
        return []


# 1. asset_group_ad 审批
print("=== asset_group_ad 层 ===")
agad = rows(
    "SELECT asset_group_ad.resource_name, asset_group_ad.state, "
    "asset_group_ad.policy_summary.approval_status "
    "FROM asset_group_ad "
    f"WHERE campaign.id = {PMAX}", "agad")
for r in agad:
    a = r.asset_group_ad
    ap = a.policy_summary.approval_status.name if a.policy_summary else "无"
    mark = " <<<" if ap not in ("APPROVED", "无") else ""
    print(f"  state={a.state.name} | 审批={ap}{mark}")

# 2. 若有非 APPROVED，拉政策细节
print("\n=== 政策细节（policy_topic_entries） ===")
for r in rows(
    "SELECT asset_group_ad.resource_name, "
    "asset_group_ad.policy_summary.policy_topic_entries.topic, "
    "asset_group_ad.policy_summary.policy_topic_entries.type "
    "FROM asset_group_ad "
    f"WHERE campaign.id = {PMAX}", "policy"):
    a = r.asset_group_ad
    ps = a.policy_summary
    if ps and ps.policy_topic_entries:
        for t in ps.policy_topic_entries:
            print(f"  {a.resource_name.split('/')[-1][:40]}: "
                  f"{t.topic} | {t.type_.name if hasattr(t, 'type_') else t.type}")

# 3. PMax 广告系列设置（final url expansion / 网址扩容）
print("\n=== campaign PMax 专属设置 ===")
for r in rows(
    f"SELECT campaign.name, campaign.status, campaign.final_url_expansion_opt_in, "
    f"campaign.url_expansion_opt_out? FROM campaign WHERE campaign.id = {PMAX}",
    "cset"):
    print(f"  {r.campaign.name}")
# final_url_expansion_opt_in 可能字段名不同，单独试
for r in rows(
    f"SELECT campaign.final_url_expansion_opt_in FROM campaign "
    f"WHERE campaign.id = {PMAX}", "fue"):
    print(f"  final_url_expansion_opt_in = {r.campaign.final_url_expansion_opt_in}")
