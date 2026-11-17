# -*- coding: utf-8 -*-
"""反射 operation 支持性 + case_value 全维度查询现有树。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

print("=== AssetGroupListingGroupFilterOperation 字段 ===")
# 仅反射 proto，不建连接：直接 import 类型
from google.ads.googleads.v26.services.types.\
    asset_group_listing_group_filter_service import (
    AssetGroupListingGroupFilterOperation as Op,
)
for f in Op.meta.fields.values():
    print(f"  {f.name}")

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

print("\n=== 现有树 case_value 全维度 ===")
q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.case_value.product_brand.value, "
    "asset_group_listing_group_filter.case_value.product_channel.channel, "
    "asset_group_listing_group_filter.case_value.product_condition.condition, "
    "asset_group_listing_group_filter.case_value.product_item_id.value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "index, "
    "asset_group_listing_group_filter.case_value.product_type.value "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)
try:
    for r in gas.search(customer_id=CID, query=q):
        f = r.asset_group_listing_group_filter
        cv = f.case_value
        dims = {
            "brand": cv.product_brand.value,
            "channel": cv.product_channel.channel,
            "cond": cv.product_condition.condition,
            "item": cv.product_item_id.value,
            "custom": cv.product_custom_attribute.value,
            "ptype": cv.product_type.value,
        }
        nz = {k: v for k, v in dims.items() if v not in (None, "", 0)}
        print(f"  id={f.id} 非空维度={nz or '全部为空(=其他所有产品桶)'}")
except Exception as e:  # noqa
    print(f"  失败: {str(e)[:500]}")
