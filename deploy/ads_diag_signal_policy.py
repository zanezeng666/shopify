# -*- coding: utf-8 -*-
"""查 asset_group_signal 审批状态 + 搜索主题词内容。"""
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
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def rows(q, label=""):
    try:
        return list(gas.search(customer_id=CID, query=q))
    except Exception as e:  # noqa: BLE001
        errs = list(getattr(e, "errors", []) or [])
        msg = errs[0].message if errs else str(e)[:120]
        print(f"  [失败:{label}] {msg[:200]}")
        return []


print("=== 1. signal 审批状态 ===")
sigs = rows(
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.approval_status "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'", "approval")
for r in sigs:
    s = r.asset_group_signal
    st = s.approval_status.name if s.approval_status else "?"
    mark = " <<<" if st != "APPROVED" else ""
    print(f"  {st:14} | {s.resource_name.split('~')[-1]}{mark}")

print("\n=== 2. 搜索主题词内容（SEARCH_THEME asset） ===")
st_assets = rows(
    "SELECT asset.resource_name, asset.name, asset.type, asset.text "
    "FROM asset WHERE asset.type = 'SEARCH_THEME' LIMIT 50", "st")
for r in st_assets:
    a = r.asset
    print(f"  {a.name[:60]} | {a.resource_name.split('/')[-1]}")

# disapproval_reasons 单独试
print("\n=== 3. 拒批原因 ===")
for r in rows(
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.disapproval_reasons "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'", "disapp"):
    s = r.asset_group_signal
    if s.disapproval_reasons:
        print(f"  {s.resource_name.split('~')[-1]}: {list(s.disapproval_reasons)}")
