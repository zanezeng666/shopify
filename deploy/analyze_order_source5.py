"""终局：列出可访问的全部 Ads 账户，逐个查 campaign 24452460184 归属。只读。"""
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

cust = client.get_service("CustomerService")
acc = cust.list_accessible_customers()
resource_names = list(acc.resource_names)
print(f"可访问账户 {len(resource_names)} 个:")
cids = [rn.split("/")[-1] for rn in resource_names]
print("  " + ", ".join(cids))

gas = client.get_service("GoogleAdsService")
for cid in cids:
    if cid == "7059800494":
        continue  # 已确认无
    try:
        r = gas.search(customer_id=cid, query=(
            "SELECT campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type "
            "FROM campaign WHERE campaign.id = 24452460184"))
        rows = list(r)
        if rows:
            for row in rows:
                c = row.campaign
                print(f"\n[命中] 账户 {cid}: {c.name!r} status={c.status.name} type={c.advertising_channel_type.name}")
        # 顺带看该账户账户名与近 3 日该 campaign 花费
        info = cust.get_customer(customer_id=cid)
        print(f"账户 {cid} descriptive_name={info.descriptive_name!r} currency={info.currency_code} tz={info.time_zone}")
    except Exception as e:
        print(f"账户 {cid} 查询失败: {str(e)[:120]}")
