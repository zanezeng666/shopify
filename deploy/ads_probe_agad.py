# -*- coding: utf-8 -*-
"""探 AssetGroupAd 字段 + 最小查询。"""
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

m = client.get_type("AssetGroupAd")
print("AssetGroupAd 字段:", list(m._pb.DESCRIPTOR.fields_by_name))

# 用 resource_name 最小查询试探
for q in (
    f"SELECT asset_group_ad.resource_name FROM asset_group_ad WHERE campaign.id = {PMAX}",
    "SELECT asset_group_ad.resource_name, asset_group_ad.state, "
    "asset_group_ad.policy_summary.approval_status FROM asset_group_ad "
    f"WHERE campaign.id = {PMAX}",
):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"[OK] {q[:60]}... -> {len(rs)} 行")
        for r in rs:
            a = r.asset_group_ad
            ap = a.policy_summary.approval_status.name if a.policy_summary else "无"
            print(f"   state={a.state.name} 审批={ap}")
        break
    except Exception as e:  # noqa: BLE001
        errs = list(getattr(e, "errors", []) or [])
        msg = errs[0].message if errs else str(e)[:120]
        print(f"[FAIL] {msg[:160]}")
