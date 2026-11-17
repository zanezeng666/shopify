# -*- coding: utf-8 -*-
"""PMax 商品池空的三项主动排查：
1. campaign 的 merchant 绑定 (shopping_settings)
2. listing_group 树节点是否存在
3. MC 账户级状态 (Merchant API accounts)
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "7059800494").replace("-", "")
CAMP = "24441391608"

# ---- Ads API init ----
from google.ads.googleads.client import GoogleAdsClient

ads = GoogleAdsClient.load_from_dict({
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "unused"),
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", CID),
    "use_proto_plus": True,
})
gac = ads.get_service("GoogleAdsService")

print("=== 1) campaign merchant 绑定 ===")
q1 = (f"SELECT campaign.id, campaign.name, campaign.status, "
      f"campaign.advertising_channel_type, "
      f"campaign.shopping_setting.merchant_id "
      f"FROM campaign WHERE campaign.id = {CAMP}")
for row in gac.search(customer_id=CID, query=q1):
    c = row.campaign
    ss = c.shopping_setting
    print(f"  campaign {c.id} '{c.name}' status={c.status.name} ch={c.advertising_channel_type.name}")
    print(f"  merchant_id={ss.merchant_id}")

print("\n=== 2) PMax 树节点 (listing_group_filter) ===")
q2 = (f"SELECT asset_group_listing_group_filter.id, "
      f"asset_group_listing_group_filter.type, "
      f"asset_group_listing_group_filter.listing_source "
      f"FROM asset_group_listing_group_filter WHERE campaign.id = {CAMP}")
n = 0
for row in gac.search(customer_id=CID, query=q2):
    n += 1
    lg = row.asset_group_listing_group_filter
    print(f"  node {lg.id} type={lg.type_.name} source={lg.listing_source.name if lg.listing_source else '?'}")
print(f"  共 {n} 个节点")

# ---- 3) MC 账户状态 ----
print("\n=== 3) MC 账户级状态 (Merchant API) ===")
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
for host_ver in ("accounts/v1", "accounts/v1beta"):
    url = f"https://merchantapi.googleapis.com/{host_ver}/accounts/136469408?view=FULL"
    r = httpx.get(url, headers={"Authorization": f"Bearer {tok}"}, timeout=60)
    if r.status_code == 200:
        j = r.json()
        print(f"  [{host_ver}] name={j.get('name')} test={j.get('accountType')}")
        b = j.get("businessInformation") or {}
        print(f"  name={((b.get('businessName')) or '')[:40]}")
        print("  raw keys:", sorted(j.keys())[:18])
        break
    print(f"  [{host_ver}] {r.status_code}: {r.text[:150]}")
