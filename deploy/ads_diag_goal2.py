# -*- coding: utf-8 -*-
"""复查 PMax 转化目标：conversion_action 层 + campaign_conversion_goal 层。"""
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


def rows(q, label=""):
    try:
        return list(gas.search(customer_id=CID, query=q))
    except Exception as e:  # noqa: BLE001
        errs = list(getattr(e, "errors", []) or [])
        msg = errs[0].message if errs else str(e)[:150]
        print(f"  [失败:{label}] {msg[:250]}")
        return []


print("=== 1. 账户转化动作现状（purchase 类 + primary） ===")
for r in rows(
    "SELECT conversion_action.id, conversion_action.name, "
    "conversion_action.category, conversion_action.status, "
    "conversion_action.primary_for_goal, "
    "conversion_action.resource_name "
    "FROM conversion_action", "ca"):
    ca = r.conversion_action
    print(f"  #{ca.id} | {ca.category.name:12} | {ca.status.name:8} | "
          f"primary={ca.primary_for_goal} | {ca.name[:45]}")

print("\n=== 2. PMax 系列级转化目标配置 ===")
for r in rows(
    "SELECT campaign_conversion_goal.resource_name, "
    "campaign_conversion_goal.campaign, "
    "campaign_conversion_goal.conversion_action, "
    "campaign_conversion_goal.biddable "
    "FROM campaign_conversion_goal "
    f"WHERE campaign_conversion_goal.campaign = "
    f"'customers/{CID}/campaigns/{PMAX}'", "ccg"):
    g = r.campaign_conversion_goal
    print(f"  biddable={g.biddable} | {g.conversion_action}")

print("\n=== 3. Search 系列级转化目标配置（对照） ===")
for r in rows(
    "SELECT campaign_conversion_goal.biddable, "
    "campaign_conversion_goal.conversion_action "
    "FROM campaign_conversion_goal "
    f"WHERE campaign_conversion_goal.campaign = "
    f"'customers/{CID}/campaigns/{SEARCH}'", "ccg2"):
    g = r.campaign_conversion_goal
    print(f"  biddable={g.biddable} | {g.conversion_action}")

print("\n=== 4. PMax 系列目标设置字段 ===")
for r in rows(
    f"SELECT campaign.name, campaign.status FROM campaign "
    f"WHERE campaign.id = {PMAX}", "c"):
    print(f"  {r.campaign.name} | {r.campaign.status.name}")
