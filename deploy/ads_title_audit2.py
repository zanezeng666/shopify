# -*- coding: utf-8 -*-
"""PMax 资产查询修复：逐组合试探 asset_group_asset 可用字段
+ asset_automation_setting 字段名。"""
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

print("=== asset_group_asset 组合试探 ===")
COMBOS = [
    ("最小", "SELECT asset_group_asset.asset_type, "
     "asset_group_asset.status FROM asset_group_asset "
     f"WHERE campaign.id = {PMAX}"),
    ("加 asset.rn", "SELECT asset_group_asset.asset_type, "
     "asset_group_asset.status, asset.resource_name "
     "FROM asset_group_asset "
     f"WHERE campaign.id = {PMAX}"),
    ("加 text", "SELECT asset_group_asset.asset_type, "
     "asset_group_asset.status, asset.resource_name, "
     "asset.text_asset.text FROM asset_group_asset "
     f"WHERE campaign.id = {PMAX}"),
    ("加 asset.name", "SELECT asset_group_asset.asset_type, "
     "asset_group_asset.status, asset.resource_name, asset.name, "
     "asset.text_asset.text FROM asset_group_asset "
     f"WHERE campaign.id = {PMAX}"),
]
for label, q in COMBOS:
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"  [{label}] OK rows={len(rs)}")
        for r in rs[:100]:
            aga = r.asset_group_asset
            txt = ""
            if r.asset and r.asset.text_asset:
                txt = (r.asset.text_asset.text or "").strip()
            print(f"    [{aga.asset_type.name:14}] {aga.status.name:9} "
                  f"{txt[:84]!r}")
        break
    except Exception as e:  # noqa
        msg = str(e)
        errs = [ln.strip() for ln in msg.split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"  [{label}] FAIL {errs[:1] or msg[:150]}")

print("\n=== asset_automation_setting 字段试探 ===")
AAS = [
    ("v1", "SELECT asset_automation_setting.asset_field_type, "
     "asset_automation_setting.asset_automation_enrollment_status "
     f"FROM asset_automation_setting WHERE campaign.id = {PMAX}"),
    ("无过滤", "SELECT asset_automation_setting.asset_field_type, "
     "asset_automation_setting.asset_automation_enrollment_status, "
     "campaign.id FROM asset_automation_setting"),
]
for label, q in AAS:
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"  [{label}] OK rows={len(rs)}")
        for r in rs:
            s = r.asset_automation_setting
            print(f"    {s.asset_field_type.name}: "
                  f"{s.asset_automation_enrollment_status.name}")
        break
    except Exception as e:  # noqa
        msg = str(e)
        errs = [ln.strip() for ln in msg.split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"  [{label}] FAIL {errs[:1] or msg[:150]}")
