# -*- coding: utf-8 -*-
"""追查异常信号 2701596989512 的身份与来源。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
BAD = 2701596989512

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
        rs = list(gas.search(customer_id=CID, query=q))
        return rs
    except Exception as e:  # noqa: BLE001
        errs = list(getattr(e, "errors", []) or [])
        msg = errs[0].message if errs else str(e)[:120]
        print(f"  [失败:{label}] {msg[:200]}")
        return []


print("=== 1. audience 视图找该 id ===")
for r in rows(
    "SELECT audience.id, audience.name, audience.status FROM audience "
    f"WHERE audience.id = {BAD}", "aud"):
    a = r.audience
    print(f"  #{a.id} {a.name} | {a.status.name if a.status else '?'}")

print("=== 2. user_list 找该 id ===")
for r in rows(
    "SELECT user_list.id, user_list.name, user_list.type, "
    "user_list.size_for_search FROM user_list "
    f"WHERE user_list.id = {BAD}", "ul"):
    u = r.user_list
    print(f"  #{u.id} {u.name} | type={u.type_.name if hasattr(u,'type_') else '?'} | "
          f"search规模={u.size_for_search}")

print("=== 3. 最近 24h 变更事件（用户后台操作痕迹） ===")
for r in rows(
    "SELECT change_event.change_date_time, change_event.user_email, "
    "change_event.client_type, change_event.resource_name "
    "FROM change_event "
    "WHERE change_event.change_date_time DURING LAST_1_DAY LIMIT 40", "ce"):
    c = r.change_event
    print(f"  {c.change_date_time} | {c.client_type.name:10} | "
          f"{(c.user_email or '?')[:28]:28} | {c.resource_name[:80]}")

print("=== 4. 该 signal 拒批原因（精确） ===")
for r in rows(
    "SELECT asset_group_signal.resource_name, asset_group_signal.approval_status, "
    "asset_group_signal.disapproval_reasons FROM asset_group_signal "
    f"WHERE asset_group_signal.resource_name = "
    f"'customers/{CID}/assetGroupSignals/6770847164~{BAD}'", "why"):
    s = r.asset_group_signal
    print(f"  status={s.approval_status.name if s.approval_status else '?'} "
          f"reasons={list(s.disapproval_reasons)}")
