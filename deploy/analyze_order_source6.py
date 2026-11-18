"""终局2：GAQL 拿 3 账户名 + campaign id 范围查询兜底。只读。"""
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

for cid in ["7059800494", "1651348739", "2214926660"]:
    try:
        r = gas.search(customer_id=cid, query=(
            "SELECT customer.descriptive_name, customer.currency_code, customer.time_zone FROM customer"))
        for row in r:
            cu = row.customer
            print(f"账户 {cid}: {cu.descriptive_name!r} {cu.currency_code} {cu.time_zone}")
        # 范围兜底
        r2 = gas.search(customer_id=cid, query=(
            "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type "
            "FROM campaign WHERE campaign.id > 24452460100 AND campaign.id < 24452460200"))
        for row in r2:
            c = row.campaign
            print(f"  [范围命中] {c.id} {c.name!r} {c.status.name} {c.advertising_channel_type.name}")
    except Exception as e:
        print(f"账户 {cid} 失败: {str(e)[:150]}")

# 主账户近 3 日全部 campaign 花费（背景：断崖后恢复情况）
print("\n[主账户 11-16~18 按日花费]")
try:
    r3 = gas.search(customer_id="7059800494", query=(
        "SELECT segments.date, metrics.cost_micros, metrics.clicks, metrics.impressions "
        "FROM campaign WHERE segments.date BETWEEN '2026-11-16' AND '2026-11-18' "
        "AND campaign.status = 'ENABLED'"))
    agg = {}
    for row in r3:
        d = row.segments.date
        a = agg.setdefault(d, [0, 0, 0])
        a[0] += row.metrics.cost_micros / 1e6
        a[1] += row.metrics.clicks
        a[2] += row.metrics.impressions
    for d in sorted(agg):
        c_, k_, i_ = agg[d]
        print(f"  {d}: ¥{c_:.2f} clicks={k_} imps={i_}")
except Exception as e:
    print(f"  失败: {str(e)[:150]}")
