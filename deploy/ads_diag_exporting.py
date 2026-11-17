# -*- coding: utf-8 -*-
"""定位 'Exporting, Manufacturer' 无效资源 v2：修正 GAQL 列名。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"
CAMP = f"customers/{CID}/campaigns/24441391608"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")


def run(label, q, fmt):
    print(f"\n===== {label} =====")
    try:
        rows = list(gas.search(customer_id=CID, query=q))
        for r in rows:
            print(" ", fmt(r))
        if not rows:
            print("  (0 行)")
    except Exception as e:  # noqa: BLE001
        print("  [FAIL]", str(e).replace("\n", " ")[:300])


# 1. 全部受众资源（含 2506363323582）
run("audiences", (
    "SELECT audience.id, audience.name, audience.status, audience.source "
    "FROM audience"), lambda r: (
    f"{r.audience.id} | {r.audience.status.name:<12} "
    f"| {r.audience.source.name:<18} | {r.audience.name[:55]}"))

# 2. AG 全部资产挂链
run("asset_group_asset", (
    "SELECT asset_group_asset.asset, asset_group_asset.field_type, "
    "asset_group_asset.status, asset.name, asset.type, "
    "asset.policy_summary.approval_status "
    "FROM asset_group_asset "
    f"WHERE asset_group_asset.asset_group = '{AG}'"), lambda r: (
    f"{r.asset_group_asset.field_type.name:<26} "
    f"{r.asset_group_asset.status.name:<8} "
    f"{getattr(r.asset.policy_summary, 'approval_status', None) and r.asset.policy_summary.approval_status.name or '-':<20} "
    f"| {r.asset.name[:50]}"))

# 3. campaign 层资产
run("campaign_asset", (
    "SELECT campaign_asset.asset, campaign_asset.field_type, "
    "campaign_asset.status, asset.name, asset.type, "
    "asset.policy_summary.approval_status "
    "FROM campaign_asset "
    f"WHERE campaign_asset.campaign = '{CAMP}'"), lambda r: (
    f"{r.campaign_asset.field_type.name:<26} "
    f"{r.campaign_asset.status.name:<8} "
    f"{getattr(r.asset.policy_summary, 'approval_status', None) and r.asset.policy_summary.approval_status.name or '-':<20} "
    f"| {r.asset.name[:50]}"))

# 4. AG 全部信号（与已验证成功版一致）
run("asset_group_signal", (
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.search_theme.text, "
    "asset_group_signal.approval_status "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'"), lambda r: (
    f"{r.asset_group_signal.approval_status.name:<12} | "
    f"{r.asset_group_signal.search_theme.text or '-'}"))
