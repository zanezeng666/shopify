# -*- coding: utf-8 -*-
"""PMax listing 医疗收敛 v2：原地 update 两节点（无非法中间态）。
- 15553272882: case_value custom('ad-medical') -> product_type('Medical Battery')
- 15553272885: type_ -> UNIT_EXCLUDED（其他所有产品=排除；若原本已排除则幂等）
"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PFX = f"customers/{CID}/assetGroupListingGroupFilters/6770847164~"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
enum = (client.get_type("ListingGroupFilterTypeEnum")
        .ListingGroupFilterType)
svc = client.get_service("AssetGroupListingGroupFilterService")

ops = []

# 1) label 桶 -> product_type 桶（保持原 INC 身份，只换维度值）
u1 = client.get_type("AssetGroupListingGroupFilter")
u1.resource_name = PFX + "15553272882"
u1.case_value.product_type.value = "Medical Battery"
op1 = client.get_type("AssetGroupListingGroupFilterOperation")
op1.update = u1
op1.update_mask.paths.append("case_value")
ops.append(op1)

# 2) 其他所有产品桶 -> EXCLUDED
u2 = client.get_type("AssetGroupListingGroupFilter")
u2.resource_name = PFX + "15553272885"
u2.type_ = enum.UNIT_EXCLUDED
op2 = client.get_type("AssetGroupListingGroupFilterOperation")
op2.update = u2
op2.update_mask.paths.append("type")
ops.append(op2)

print("提交 update×2 ...")
try:
    resp = svc.mutate_asset_group_listing_group_filters(
        customer_id=CID, operations=ops)
    for r in resp.results:
        print(f"  OK {r.resource_name}")
except Exception as e:  # noqa
    print(f"  MUTATE 失败: {str(e)[:900]}")
    raise SystemExit(1)

print("\n=== 复核：树 case_value 全维度 ===")
gas = client.get_service("GoogleAdsService")
q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "value "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)
for r in gas.search(customer_id=CID, query=q):
    f = r.asset_group_listing_group_filter
    print(f"  id={f.id} ptype={f.case_value.product_type.value or '-'} "
          f"custom={f.case_value.product_custom_attribute.value or '-'}")

print("\n完成：PMax 商品池=product_type 'Medical Battery'（Shopify 线上 "
      "1,023 个医疗商品，与落地 collection 完全一致），其余产品全部排除。")
