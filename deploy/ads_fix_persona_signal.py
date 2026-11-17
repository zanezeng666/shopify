# -*- coding: utf-8 -*-
"""处理 UNSPECIFIED persona 信号：确认 audience 引用 → REMOVE → readback。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"
BAD = f"customers/{CID}/assetGroupSignals/6770847164~2506363323582"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# 1. 查该信号 audience 引用（两种列名探测）
for col in ("asset_group_signal.audience.resource_name",
            "asset_group_signal.audience"):
    try:
        rows = list(gas.search(customer_id=CID, query=(
            f"SELECT {col}, asset_group_signal.approval_status "
            "FROM asset_group_signal "
            f"WHERE asset_group_signal.resource_name = '{BAD}'")))
        for r in rows:
            print("aud:", col, "->",
                  getattr(r.asset_group_signal.audience, "resource_name",
                          r.asset_group_signal.audience),
                  "| status:", r.asset_group_signal.approval_status.name)
        break
    except Exception as e:  # noqa: BLE001
        print("[col fail]", col, str(e).replace("\n", " ")[:120])

# 2. REMOVE 无效信号
svc = client.get_service("AssetGroupSignalService")
op = client.get_type("AssetGroupSignalOperation")
op.remove = BAD
res = svc.mutate_asset_group_signals(customer_id=CID, operations=[op])
print("removed:", res.results[0].resource_name)

# 3. readback
rows = list(gas.search(customer_id=CID, query=(
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.search_theme.text, "
    "asset_group_signal.approval_status "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'")))
from collections import Counter  # noqa: E402
cnt = Counter(r.asset_group_signal.approval_status.name for r in rows)
print(f"readback 信号数={len(rows)} 状态分布={dict(cnt)}")
for r in rows:
    if not r.asset_group_signal.search_theme.text:
        print("残留非主题信号:", r.asset_group_signal.resource_name,
              r.asset_group_signal.approval_status.name)
