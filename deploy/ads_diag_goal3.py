# -*- coding: utf-8 -*-
"""探目标配置资源字段 + 查 PMax 系列级目标配置。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
SEARCH = 24448362668

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

for t in ("CampaignConversionGoal", "ConversionGoalCampaignConfig",
          "CustomConversionGoal"):
    try:
        m = client.get_type(t)
        print(f"{t} 字段: {list(m._pb.DESCRIPTOR.fields_by_name)}")
    except ValueError:
        print(f"{t}: 不存在")


def rows(q, label=""):
    try:
        return list(gas.search(customer_id=CID, query=q))
    except Exception as e:  # noqa: BLE001
        errs = list(getattr(e, "errors", []) or [])
        msg = errs[0].message if errs else str(e)[:150]
        print(f"  [失败:{label}] {msg[:250]}")
        return []


print("\n=== conversion_goal_campaign_config（两个系列） ===")
for r in rows(
    "SELECT conversion_goal_campaign_config.campaign, "
    "conversion_goal_campaign_config.level, "
    "conversion_goal_campaign_config.custom_conversion_goal "
    "FROM conversion_goal_campaign_config", "cfg"):
    c = r.conversion_goal_campaign_config
    print(f"  campaign={c.campaign.split('/')[-1]} | level={c.level.name} | "
          f"custom_goal={c.custom_conversion_goal or '-'}")

print("\n=== custom_conversion_goal 全表 ===")
for r in rows(
    "SELECT custom_conversion_goal.id, custom_conversion_goal.name, "
    "custom_conversion_goal.status, custom_conversion_goal.conversion_actions "
    "FROM custom_conversion_goal", "ccg"):
    g = r.custom_conversion_goal
    acts = list(g.conversion_actions)
    print(f"  #{g.id} {g.name} | {g.status.name} | 含 {len(acts)} 个动作")

print("\n=== campaign_conversion_goal（全表，不加过滤） ===")
for r in rows(
    "SELECT campaign_conversion_goal.resource_name, "
    "campaign_conversion_goal.biddable "
    "FROM campaign_conversion_goal LIMIT 50", "ccg-all"):
    g = r.campaign_conversion_goal
    print(f"  biddable={g.biddable} | {g.resource_name}")
