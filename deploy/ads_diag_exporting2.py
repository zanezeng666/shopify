# -*- coding: utf-8 -*-
"""查 audience 资源详情 + custom_segment，确认 'Exporting, Manufacturer' 来源。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"

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
        print("  [FAIL]", str(e).replace("\n", " ")[:260])


# 1. audience 最小列
run("audiences(min)", (
    "SELECT audience.id, audience.name, audience.status FROM audience"),
    lambda r: f"{r.audience.id} | {r.audience.status.name:<12} | "
              f"{r.audience.name[:60]}")

# 2. 挂在 AG 上的信号受众 resource_name（拿 id）
run("signal audience rn", (
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.approval_status "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'"), lambda r: (
    f"{r.asset_group_signal.approval_status.name:<12} | "
    f"{r.asset_group_signal.resource_name}"))

# 3. 自定义细分
run("custom_segment", (
    "SELECT custom_segment.id, custom_segment.name, custom_segment.status "
    "FROM custom_segment"), lambda r: (
    f"{r.custom_segment.id} | {getattr(r.custom_segment.status, 'name', '-')} "
    f"| {r.custom_segment.name[:60]}"))
