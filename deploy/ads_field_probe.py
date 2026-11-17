# -*- coding: utf-8 -*-
"""逐字段测 GAQL 可用性，定位 UNRECOGNIZED_FIELD 元凶。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = 6770847164
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

aga_fields = [
    "asset_group_asset.resource_name",
    "asset_group_asset.status",
    "asset_group_asset.field_type",
    "asset_group_asset.added_by_google_ads",
    "asset.name",
    "asset.text_asset.text",
]
print("=== asset_group_asset 逐字段（WHERE asset_group.id） ===")
for f in aga_fields:
    try:
        n = len(list(gas.search(
            customer_id=CID,
            query=f"SELECT {f} FROM asset_group_asset "
                  f"WHERE asset_group.id = {AG}")))
        print(f"  ✓ {f} ({n}行)")
    except Exception as e:
        print(f"  ✗ {f}")

print("\n=== asset_automation_setting 逐字段 ===")
for f in ("asset_automation_setting.resource_name",
          "asset_automation_setting.asset_automation_type",
          "asset_automation_setting.field_type",
          "asset_automation_setting.status"):
    try:
        rs = list(gas.search(
            customer_id=CID,
            query=f"SELECT {f} FROM asset_automation_setting "
                  f"WHERE campaign.id = {PMAX}"))
        print(f"  ✓ {f} ({len(rs)}行)")
    except Exception as e:
        print(f"  ✗ {f}")

# WHERE 条件本身可用性
print("\n=== WHERE 条件测试（select resource_name） ===")
for w in (f"asset_group.id = {AG}", "campaign.id = " + str(PMAX)):
    try:
        rs = list(gas.search(
            customer_id=CID,
            query=f"SELECT asset_group_asset.resource_name "
                  f"FROM asset_group_asset WHERE {w}"))
        print(f"  ✓ WHERE {w} ({len(rs)}行)")
    except Exception as e:
        print(f"  ✗ WHERE {w}")
