"""change_event 重查：.name 枚举修复 + 类型分布。只读。"""
import os
from collections import Counter

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

r = gas.search(customer_id="7059800494", query=(
    "SELECT change_event.change_date_time, change_event.user_email, change_event.client_type, "
    "change_event.change_resource_type, change_event.changed_fields "
    "FROM change_event "
    "WHERE change_event.change_date_time BETWEEN '2026-11-14 00:00:00' AND '2026-11-18 23:59:59' "
    "LIMIT 10000"))
types = Counter()
camp_rows = []
for row in r:
    ce = row.change_event
    t = ce.change_resource_type.name if hasattr(ce.change_resource_type, "name") else str(ce.change_resource_type)
    types[t] += 1
    if t == "CAMPAIGN":
        fields = ",".join(list(ce.changed_fields.paths)[:5])[:70]
        camp_rows.append(f"{ce.change_date_time[:19]} {str(ce.user_email)[:24]:<24} "
                         f"{str(ce.client_type):<14} {fields}")
print(f"变更类型分布: {dict(types)}")
print(f"\nCAMPAIGN 变更 {len(camp_rows)} 条：")
for c in camp_rows:
    print(f"  {c}")
