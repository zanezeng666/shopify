# -*- coding: utf-8 -*-
"""只读验证 v2：打印全部信号 id+审批状态，人工判别受众类。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = 6770847164

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

q = (
    "SELECT asset_group_signal.resource_name, "
    "asset_group_signal.approval_status "
    "FROM asset_group_signal "
    f"WHERE asset_group_signal.asset_group = 'customers/{CID}/assetGroups/{AG}'")
rows = list(gas.search(customer_id=CID, query=q))
print(f"信号总数: {len(rows)}\n")
for r in rows:
    s = r.asset_group_signal
    tail = s.resource_name.split("/")[-1]          # 6770847164~<signal_id>
    sid = tail.split("~")[-1] if "~" in tail else tail
    kind = "受众?" if (sid.isdigit() and len(sid) >= 11) else "主题?"
    print(f"  signal_id={sid:22} {kind} | {s.approval_status.name}")
