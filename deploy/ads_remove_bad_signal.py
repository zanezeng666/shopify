# -*- coding: utf-8 -*-
"""移除被拒的受众信号（自定义细分残留），readback 确认。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
BAD_RN = f"customers/{CID}/assetGroupSignals/6770847164~2701596989512"
AG = f"customers/{CID}/assetGroups/6770847164"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
ags = client.get_service("AssetGroupSignalService")
gas = client.get_service("GoogleAdsService")

# 1. 移除被拒信号（只解除关联，不删账户资源，可逆）
op = client.get_type("AssetGroupSignalOperation")
op.remove = BAD_RN
try:
    res = ags.mutate_asset_group_signals(customer_id=CID, operations=[op])
    print("[OK] 已移除:", res.results[0].resource_name)
except Exception as e:  # noqa: BLE001
    errs = list(getattr(e, "errors", []) or [])
    msg = errs[0].message if errs else str(e)[:200]
    print("[FAIL]", msg[:300])

# 2. readback：剩余信号应全为 APPROVED
rows = list(gas.search(customer_id=CID, query=(
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.approval_status "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'")))
print(f"\nreadback: 剩余信号 {len(rows)} 条")
bad_left = 0
for r in rows:
    s = r.asset_group_signal
    st = s.approval_status.name if s.approval_status else "UNSPECIFIED"
    if st != "APPROVED":
        bad_left += 1
        print(f"  [仍异常] {st} | {s.resource_name.split('~')[-1]}")
print(f"非 APPROVED 信号数: {bad_left}")
