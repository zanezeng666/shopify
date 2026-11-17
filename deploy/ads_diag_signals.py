# -*- coding: utf-8 -*-
"""最小化试探 asset_group_signal / custom_segment 查询姿势。"""
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

TESTS = [
    ("signal 按 asset_group 过滤（最小列）",
     f"SELECT asset_group_signal.resource_name FROM asset_group_signal "
     f"WHERE asset_group_signal.asset_group = '{AG}'"),
    ("signal 含 search_theme 列",
     f"SELECT asset_group_signal.search_theme.resource_name, "
     f"asset_group_signal.audience.resource_name "
     f"FROM asset_group_signal WHERE asset_group_signal.asset_group = '{AG}'"),
    ("asset 按 type 过滤",
     "SELECT asset.resource_name, asset.name FROM asset "
     "WHERE asset.type = 'SEARCH_THEME'"),
    ("custom_segment 最小列",
     "SELECT custom_segment.id, custom_segment.name FROM custom_segment"),
]

for label, query in TESTS:
    try:
        rows = list(gas.search(customer_id=CID, query=query))
        print(f"[OK] {label}: {len(rows)} 行")
        for r in rows[:15]:
            print("   ", r)
    except Exception as e:  # noqa: BLE001
        msg = ""
        if hasattr(e, "errors") and e.errors:
            for er in e.errors:
                msg += (er.message or "")[:150] + " | "
        print(f"[FAIL] {label}: {msg or str(e)[:150]}")
