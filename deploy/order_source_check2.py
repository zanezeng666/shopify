"""change_event 修正版：分段拉 11-15~18 全部变更，grep campaign/24452460184 痕迹。只读。"""
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
ranges = [("2026-11-15 00:00:00", "2026-11-16 00:00:00"),
          ("2026-11-16 00:00:00", "2026-11-17 00:00:00"),
          ("2026-11-17 00:00:00", "2026-11-18 23:59:59")]
total_all, target_lines, camp_events = 0, [], []
for lo, hi in ranges:
    q = ("SELECT change_event.change_date_time, change_event.change_resource_name, "
         "change_event.change_status_type, change_event.user_email, change_event.client_type, "
         "change_event.changed_fields FROM change_event "
         f"WHERE change_event.change_date_time >= '{lo}' "
         f"AND change_event.change_date_time <= '{hi}' LIMIT 10000")
    try:
        r = gas.search(customer_id="7059800494", query=q)
        n = 0
        for row in r:
            ce = row.change_event
            n += 1
            line = (f"{ce.change_date_time} | {ce.change_resource_name} | "
                    f"{ce.change_status_type.name} | {ce.user_email} | {ce.client_type.name}")
            if TARGET in ce.change_resource_name:
                target_lines.append(line)
            elif "/campaigns/" in ce.change_resource_name:
                camp_events.append(line)
        total_all += n
        print(f"{lo[:10]}: {n} 条变更")
    except Exception as e:
        print(f"{lo[:10]}: 失败 {str(e)[:150]}")

print(f"\n合计 {total_all} 条；目标 {TARGET} 命中 {len(target_lines)} 条")
for t in target_lines:
    print(f"  ★ {t}")
print(f"\ncampaign 资源变更共 {len(camp_events)} 条（样本，看创建/删除）")
for c in camp_events[:40]:
    print(f"  {c}")
