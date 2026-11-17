# -*- coding: utf-8 -*-
"""元数据字典查真实字段名 + PMax 资产组资产全量审计。"""
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
BAD_WORDS = ("jbl", "bose", "craftsman", "styles")

print("=== 元数据：asset_automation 相关字段 ===")
try:
    for r in gas.search(customer_id=CID, query=(
            "SELECT google_ads_field.name, google_ads_field.resource_name "
            "FROM google_ads_field "
            "WHERE google_ads_field.name LIKE 'asset_automation%'")):
        print(f"  {r.google_ads_field.name}")
except Exception as e:  # noqa
    print(f"  失败: {str(e)[:200]}")

print("\n=== 元数据：asset_group_asset 可选字段（field_type 相关）===")
try:
    for r in gas.search(customer_id=CID, query=(
            "SELECT google_ads_field.name "
            "FROM google_ads_field "
            "WHERE google_ads_field.name LIKE 'asset_group_asset.%'")):
        print(f"  {r.google_ads_field.name}")
except Exception as e:  # noqa
    print(f"  失败: {str(e)[:200]}")

print("\n=== PMax 资产组资产全量（field_type 版）===")
try:
    n = hit = 0
    for r in gas.search(customer_id=CID, query=(
            "SELECT asset_group_asset.field_type, asset_group_asset.status, "
            "asset.resource_name, asset.text_asset.text "
            f"FROM asset_group_asset WHERE campaign.id = {PMAX}")):
        aga = r.asset_group_asset
        txt = (r.asset.text_asset.text or "").strip() if (
            r.asset and r.asset.text_asset) else ""
        n += 1
        low = txt.lower()
        mark = "  ◀◀◀" if any(w in low for w in BAD_WORDS) else ""
        hit += 1 if mark else 0
        print(f"  [{aga.field_type.name:14}] {aga.status.name:9} "
              f"{txt[:84]!r}{mark}")
    print(f"  共 {n} 个，含旧品牌词 {hit} 个")
except Exception as e:  # noqa
    msg = str(e)
    errs = [ln.strip() for ln in msg.split("\n")
            if "Unrecognized" in ln or "message:" in ln.lower()]
    print(f"  FAIL {errs[:1] or msg[:200]}")

print("\n=== campaign.asset_automation_settings 探查 ===")
for q in (
    "SELECT campaign.asset_automation_settings FROM campaign "
    f"WHERE campaign.id = {PMAX}",
    "SELECT campaign.name, campaign.asset_automation_settings "
    f"FROM campaign WHERE campaign.id = {PMAX}",
):
    try:
        for r in gas.search(customer_id=CID, query=q):
            for s in (r.campaign.asset_automation_settings or []):
                print(f"  {s.asset_field_type}: "
                      f"{s.asset_automation_enrollment_status}")
        break
    except Exception as e:  # noqa
        msg = str(e)
        errs = [ln.strip() for ln in msg.split("\n")
                if "Unrecognized" in ln or "message:" in ln.lower()]
        print(f"  FAIL {errs[:1] or msg[:200]}")
