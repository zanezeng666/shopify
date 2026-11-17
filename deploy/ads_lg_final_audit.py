# -*- coding: utf-8 -*-
"""28885 全维度含 bidding_category 终查。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.case_value.product_brand.value, "
    "asset_group_listing_group_filter.case_value.product_item_id.value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "index, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_bidding_category."
    "level, "
    "asset_group_listing_group_filter.case_value.product_bidding_category."
    "id "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)
for r in gas.search(customer_id=CID, query=q):
    f = r.asset_group_listing_group_filter
    cv = f.case_value
    print(f"id={f.id} brand={cv.product_brand.value!r} "
          f"item={cv.product_item_id.value!r} "
          f"custom={cv.product_custom_attribute.value!r} "
          f"custom_idx={cv.product_custom_attribute.index} "
          f"ptype={cv.product_type.value!r} "
          f"bidcat_level={cv.product_bidding_category.level} "
          f"bidcat_id={cv.product_bidding_category.id}")
