"""双路：① change_event(BETWEEN 正确格式)看 campaign 变更动作 ② change_status 拿 resource_name 直接 grep 目标 id。只读。"""
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

TARGET = "24452460184"

# --- ① change_event：11-15~18 变更，过滤 CAMPAIGN 资源 ---
print("[change_event 11-15~18] CAMPAIGN 相关变更：")
try:
    r = gas.search(customer_id="7059800494", query=(
        "SELECT change_event.change_date_time, change_event.user_email, change_event.client_type, "
        "change_event.change_resource_type, change_event.change_status_type, change_event.changed_fields "
        "FROM change_event "
        "WHERE change_event.change_date_time BETWEEN '2026-11-15 00:00:00' AND '2026-11-18 23:59:59' "
        "LIMIT 10000"))
    n = camp = 0
    for row in r:
        ce = row.change_event
        n += 1
        if ce.change_resource_type_.name if hasattr(ce.change_resource_type_, 'name') else True:
            pass
        rt = ce.change_resource_type
        rt_name = rt.name if rt else "?"
        if rt_name == "CAMPAIGN":
            camp += 1
            fields = ",".join(list(ce.changed_fields)[:4])[:60]
            print(f"  {ce.change_date_time[:19]} {ce.change_status_type.name:<8} "
                  f"{ce.user_email[:24]:<24} {ce.client_type.name:<14} {fields}")
    print(f"  （总变更 {n} 条，其中 CAMPAIGN {camp} 条）")
except Exception as e:
    print(f"  失败: {str(e)[:200]}")

# --- ② change_status：resource_name 直接 grep ---
print("\n[change_status] 目标 id 痕迹：")
try:
    r2 = gas.search(customer_id="7059800494", query=(
        "SELECT change_status.resource_name, change_status.resource_type, "
        "change_status.resource_status, change_status.last_change_date_time FROM change_status"))
    hit = 0
    for row in r2:
        cs = row.change_status
        if TARGET in cs.resource_name:
            hit += 1
            print(f"  ★ {cs.resource_name} | {cs.resource_status.name} | {cs.last_change_date_time}")
    if not hit:
        print(f"  30 天内无 {TARGET} 的任何变更痕迹")
except Exception as e:
    print(f"  失败: {str(e)[:200]}")
