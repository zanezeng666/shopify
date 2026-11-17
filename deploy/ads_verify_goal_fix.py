# -*- coding: utf-8 -*-
"""只读复核：PMax 转化目标配置（用户后台手工修复后验证）。"""
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

# 探字段名（上次没跑成）
for t in ("CampaignConversionGoal", "ConversionGoalCampaignConfig",
          "CustomConversionGoal"):
    try:
        m = client.get_type(t)
        print(f"[{t}] 字段: {list(m._pb.DESCRIPTOR.fields_by_name)}")
    except ValueError:
        print(f"[{t}] v26 不存在")


def rows(q, label=""):
    try:
        return list(gas.search(customer_id=CID, query=q))
    except Exception as e:  # noqa: BLE001
        errs = list(getattr(e, "errors", []) or [])
        msg = errs[0].message if errs else str(e)[:150]
        print(f"  [失败:{label}] {msg[:250]}")
        return []


print("\n=== 1. 系列级目标配置（conversion_goal_campaign_config） ===")
for r in rows(
    "SELECT conversion_goal_campaign_config.campaign, "
    "conversion_goal_campaign_config.level, "
    "conversion_goal_campaign_config.custom_conversion_goal "
    "FROM conversion_goal_campaign_config", "cfg"):
    c = r.conversion_goal_campaign_config
    print(f"  campaign={c.campaign.split('/')[-1]} | "
          f"level={c.level.name} | "
          f"custom_goal={c.custom_conversion_goal or '-'}")

print("\n=== 2. PMax 系列转化目标（campaign_conversion_goal） ===")
for r in rows(
    "SELECT campaign_conversion_goal.resource_name, "
    "campaign_conversion_goal.biddable "
    "FROM campaign_conversion_goal "
    f"WHERE campaign_conversion_goal.campaign = "
    f"'customers/{CID}/campaigns/{PMAX}'", "ccg"):
    g = r.campaign_conversion_goal
    print(f"  biddable={g.biddable} | {g.resource_name.split('/')[-1][:60]}")

print("\n=== 3. 自定义目标（custom_conversion_goal） ===")
for r in rows(
    "SELECT custom_conversion_goal.id, custom_conversion_goal.name, "
    "custom_conversion_goal.status "
    "FROM custom_conversion_goal", "ccgoal"):
    g = r.custom_conversion_goal
    print(f"  #{g.id} {g.name} | {g.status.name}")

print("\n=== 4. PURCHASE/主要转化动作快照 ===")
for r in rows(
    "SELECT conversion_action.id, conversion_action.name, "
    "conversion_action.category, conversion_action.status, "
    "conversion_action.primary_for_goal "
    "FROM conversion_action "
    "WHERE conversion_action.category IN ('PURCHASE','BEGIN_CHECKOUT',"
    "'ADD_TO_CART','CONTACT','SUBMIT_LEAD_FORM')", "ca"):
    ca = r.conversion_action
    print(f"  #{ca.id} | {ca.category.name:18} | {ca.status.name:8} | "
          f"primary={ca.primary_for_goal} | {ca.name[:45]}")
