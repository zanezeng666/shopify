# -*- coding: utf-8 -*-
"""修复 PMax Medical Estry 商品树包含节点：
'medical battery'/LEVEL2 (匹配0商品) → 'Medical Battery'/LEVEL1 (1177商品)
优先 update case_value；失败则 remove+create 原子重建。
"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v26.enums.types.\
    listing_group_filter_product_type_level import (
    ListingGroupFilterProductTypeLevelEnum,
)
from google.ads.googleads.v26.enums.types.\
    listing_group_filter_listing_source import (
    ListingGroupFilterListingSourceEnum,
)
from google.protobuf import field_mask_pb2

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG = "6770847164"
ROOT_ID = "15579051589"
BAD_ID = "15579051592"
AG_RN = f"customers/{CID}/assetGroups/{AG}"
BAD_RN = f"customers/{CID}/assetGroupListingGroupFilters/{AG}~{BAD_ID}"
ROOT_RN = f"customers/{CID}/assetGroupListingGroupFilters/{AG}~{ROOT_ID}"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
ET = client.get_type("ListingGroupFilterTypeEnum").ListingGroupFilterType
LEVEL1 = (ListingGroupFilterProductTypeLevelEnum
          .ListingGroupFilterProductTypeLevel.LEVEL1)
LS = ListingGroupFilterListingSourceEnum.ListingGroupFilterListingSource
svc = client.get_service("AssetGroupListingGroupFilterService")
gas = client.get_service("GoogleAdsService")

Q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_type.level "
    "FROM asset_group_listing_group_filter "
    f"WHERE campaign.id = 24441391608"
)


def dump(title):
    print(f"=== {title} ===")
    for r in gas.search(customer_id=CID, query=Q):
        f = r.asset_group_listing_group_filter
        print(f"- id={f.id} {f.type_.name:<15} "
              f"ptype={f.case_value.product_type.value!r} "
              f"level={f.case_value.product_type.level}")


def show_err(e):
    gerr = getattr(e, "failure", None)
    if gerr is not None:
        for er in gerr.errors:
            print(f"  FAIL {er.error_code} {er.message!r}")
    else:
        print(f"  FAIL {str(e)[:400]}")


dump("修复前")

# ---- remove + create 原子重建（update 已证实静默不生效） ----
try:
    newf = client.get_type("AssetGroupListingGroupFilter")
    newf.resource_name = (
        f"customers/{CID}/assetGroupListingGroupFilters/{AG}~-2")
    newf.asset_group = AG_RN
    newf.parent_listing_group_filter = ROOT_RN
    newf.type_ = ET.UNIT_INCLUDED
    newf.listing_source = LS.SHOPPING
    newf.case_value.product_type.value = "Medical Battery"
    newf.case_value.product_type.level = LEVEL1
    cop = client.get_type("AssetGroupListingGroupFilterOperation")
    cop.create = newf
    rop = client.get_type("AssetGroupListingGroupFilterOperation")
    rop.remove = BAD_RN
    resp = svc.mutate_asset_group_listing_group_filters(
        customer_id=CID, operations=[cop, rop])
    print("REMOVE+CREATE OK:", [r.resource_name for r in resp.results])
except Exception as e2:  # noqa
    show_err(e2)
    raise SystemExit("remove+create 失败，树保持原状")

dump("修复后")
print("\n完成：包含桶=LEVEL1 'Medical Battery'（镜像库 1177 商品同值），"
      "其余保持排除")
