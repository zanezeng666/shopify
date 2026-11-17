# -*- coding: utf-8 -*-
"""给 PMax asset group 挂受众群体信号（GA4 再营销列表，'您的数据'类）。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = f"customers/{CID}/assetGroups/6770847164"
# 信号列表：历史购买者(最强) + GA4全站访客 + Ads历史转化者
SIGNALS = [
    (7248064325, "Purchasers of bomibattery - GA4"),
    (7248682486, "All Users of bomibattery - GA4"),
    (812337396, "All Converters"),
]

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
ags = client.get_service("AssetGroupSignalService")
gas = client.get_service("GoogleAdsService")

ops = []
for uid, name in SIGNALS:
    op = client.get_type("AssetGroupSignalOperation")
    sig = op.create
    sig.asset_group = AG
    sig.audience.audience = f"customers/{CID}/audiences/{uid}"
    ops.append((name, op))

for name, op in ops:
    try:
        res = ags.mutate_asset_group_signals(
            customer_id=CID, operations=[op])
        print(f"[OK] {name} -> {res.results[0].resource_name}")
    except Exception as e:  # noqa: BLE001
        s = str(e)
        tag = "已存在" if "ALREADY" in s.upper() or "duplicate" in s.lower() else "失败"
        print(f"[{tag}] {name}: {s[:180]}")

# readback：信号总数（原 10 条 search_theme + 新增受众）
rows = list(gas.search(customer_id=CID, query=(
    "SELECT asset_group_signal.resource_name FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = '{AG}'")))
print(f"\nreadback: asset group 现有信号总数 = {len(rows)}（原 10 条搜索主题）")
