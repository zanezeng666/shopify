# -*- coding: utf-8 -*-
"""诊断层2修正版：asset 层政策状态 + business_name。"""
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


def rows(q):
    return list(gas.search(customer_id=CID, query=q))


# 0. 拿 PMax 的 20 个 asset resource_name
aga = rows(
    "SELECT asset_group_asset.asset FROM asset_group_asset "
    f"WHERE campaign.id = {PMAX}")
rns = [r.asset_group_asset.asset for r in aga]
in_list = ", ".join(f'"{n}"' for n in rns)

# 1. asset 层政策状态 + 名称
print("=== PMax 20 素材 asset 层状态 ===")
for r in rows(
    "SELECT asset.resource_name, asset.name, asset.type, "
    "asset.policy_summary.approval_status "
    f"FROM asset WHERE asset.resource_name IN ({in_list})"
):
    a = r.asset
    ap = a.policy_summary.approval_status.name if a.policy_summary else "无政策项"
    mark = " <<<" if ap not in ("APPROVED", "无政策项") else ""
    print(f"  [{a.type.name:22}] {ap:12} | {a.name[:70]}{mark}")

# 2. asset_group 商家名称等字段
print("\n=== asset_group 业务字段 ===")
for r in rows(
    "SELECT asset_group.id, asset_group.name, asset_group.business_name, "
    f"asset_group.ad_strength FROM asset_group WHERE campaign.id = {PMAX}"
):
    g = r.asset_group
    print(f"  {g.name} | business_name={g.business_name!r} | "
          f"ad_strength={g.ad_strength.name}")
