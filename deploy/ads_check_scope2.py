# -*- coding: utf-8 -*-
"""最小集验证 PMax 定向。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def try_q(label, q):
    try:
        rs = list(gas.search(customer_id=CID, query=q))
        print(f"  ✓ {label} ({len(rs)}行)")
        return rs
    except Exception as e:  # noqa: BLE001
        print(f"  ✗ {label}: {str(e)[:90]}")
        return None


ls = try_q("listing_scope",
           "SELECT listing_scope.resource_name, listing_scope.listing_scope "
           "FROM listing_scope")
for r in (ls or []):
    rn = r.listing_scope.resource_name
    if f"campaigns/{PMAX}" in rn:
        print(f"  PMax 系列 scope: {rn.split('/')[-1][:60]}")
        for sc in r.listing_scope.listing_scope:
            dv = sc.dimension_value
            print(f"    维度: {dv}")

try_q("campaign 基本信息",
      "SELECT campaign.name, campaign.status, "
      "campaign.shopping_setting.merchant_center_id, "
      "campaign.shopping_setting.sales_country "
      "FROM campaign WHERE campaign.id = " + str(PMAX))

aglg = try_q("资产组 filter",
             "SELECT asset_group_listing_group_filter.resource_name, "
             "asset_group_listing_group_filter.listing_source, "
             "asset_group.id "
             "FROM asset_group_listing_group_filter")
for r in (aglg or []):
    if f"campaigns/{PMAX}" in r.asset_group_listing_group_filter. \
            resource_name or True:
        print(f"  资产组[{r.asset_group.id}] "
              f"source={r.asset_group_listing_group_filter.listing_source.name}"
              f" {r.asset_group_listing_group_filter.resource_name[-30:]}")
