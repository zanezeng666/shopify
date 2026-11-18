"""change_event 严格复刻成功字段集；change_status 最小字段。只读。"""
import os

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = client.get_service("GoogleAdsService")

# --- ① 成功格式复刻（字段集与 ads_change_history3.py 完全一致）---
print("[change_event 11-15~18 全部变更，过滤展示] ")
try:
    r = gas.search(customer_id="7059800494", query=(
        "SELECT change_event.change_date_time, change_event.user_email, change_event.client_type, "
        "change_event.change_resource_type, change_event.changed_fields "
        "FROM change_event "
        "WHERE change_event.change_date_time BETWEEN '2026-11-15 00:00:00' AND '2026-11-18 23:59:59' "
        "LIMIT 10000"))
    n = camp = 0
    for row in r:
        ce = row.change_event
        n += 1
        if str(ce.change_resource_type) == "CAMPAIGN":
            camp += 1
            fields = ",".join(list(ce.changed_fields)[:5])[:70]
            print(f"  {ce.change_date_time[:19]} {str(ce.user_email)[:24]:<24} "
                  f"{str(ce.client_type):<14} {fields}")
    print(f"  总 {n} 条 / CAMPAIGN {camp} 条")
except Exception as e:
    print(f"  失败: {str(e)[:180]}")

# --- ② change_status 最小字段 ---
print("\n[change_status 最小字段]")
try:
    r2 = gas.search(customer_id="7059800494", query=(
        "SELECT change_status.resource_name, change_status.last_change_date_time "
        "FROM change_status LIMIT 10000"))
    tgt, camp_names = 0, []
    for row in r2:
        cs = row.change_status
        if "24452460184" in cs.resource_name:
            tgt += 1
            print(f"  ★ {cs.resource_name} {cs.last_change_date_time}")
        elif "/campaigns/" in cs.resource_name:
            camp_names.append((cs.resource_name.split("/")[-1], cs.last_change_date_time[:19]))
    print(f"  目标命中 {tgt}；campaign 变更资源 {len(camp_names)} 个")
    for c in camp_names[:25]:
        print(f"    {c}")
except Exception as e:
    print(f"  失败: {str(e)[:180]}")
