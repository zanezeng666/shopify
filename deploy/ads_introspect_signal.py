# -*- coding: utf-8 -*-
"""探 CustomIntent/AssetGroupSignal 结构 + 查可用再营销列表。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

for t in ("CustomIntent", "CustomIntentMember", "AssetGroupSignal", "AudienceInfo"):
    try:
        m = client.get_type(t)
        fields = list(m._pb.DESCRIPTOR.fields_by_name)
        print(f"{t} 字段: {fields}")
    except ValueError as e:
        print(f"{t}: 不存在 ({e})")

try:
    svc = client.get_service("CustomIntentService")
    print("CustomIntentService 可用:", svc.__class__.__name__)
except Exception as e:  # noqa: BLE001
    print("CustomIntentService 不可用:", str(e)[:150])

print("\n=== 现有 custom_intent ===")
try:
    rows = list(gas.search(customer_id=CID, query=(
        "SELECT custom_intent.id, custom_intent.name, custom_intent.state "
        "FROM custom_intent")))
    print(f"共 {len(rows)} 个")
    for r in rows[:10]:
        ci = r.custom_intent
        print(f"  #{ci.id} {ci.name} | {ci.state.name if ci.state else '?'}")
except Exception as e:  # noqa: BLE001
    print("查询失败:", str(e)[:300])

print("\n=== 再营销列表（有搜索成员的） ===")
try:
    rows = list(gas.search(customer_id=CID, query=(
        "SELECT user_list.resource_name, user_list.name, "
        "user_list.size_range_for_search, user_list.type "
        "FROM user_list WHERE user_list.size_for_search > 0 LIMIT 20")))
    print(f"共 {len(rows)} 个")
    for r in rows:
        u = r.user_list
        print(f"  {u.name} | {u.size_range_for_search.name} | {u.resource_name}")
except Exception as e:  # noqa: BLE001
    print("查询失败:", str(e)[:300])
