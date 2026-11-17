# -*- coding: utf-8 -*-
"""序列 E3：树已空（F1 已删）。三 op 单请求建树：
root(SUBDIVISION, 无 case_value) + medical(INC, product_type 实值)
+ else(EXC, 显式空 case_value)。
依据：F2b 实证 root 禁 case_value；E 实证 else 桶缺 case_value 报 REQUIRED。"""
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

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_ID = "6770847164"
AG_RN = f"customers/{CID}/assetGroups/{AG_ID}"
PFX = f"customers/{CID}/assetGroupListingGroupFilters/{AG_ID}~"

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

q_tree = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.listing_source, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "value "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)


def dump_tree(title):
    print(f"=== {title} ===")
    n = 0
    for r in gas.search(customer_id=CID, query=q_tree):
        f = r.asset_group_listing_group_filter
        print(f"  id={f.id} type={f.type_.name} src={f.listing_source.name} "
              f"ptype={f.case_value.product_type.value or '-'} "
              f"custom={f.case_value.product_custom_attribute.value or '-'}")
        n += 1
    if not n:
        print("  (空树：asset group 无 listing group filter)")


def mk_create(rn, ftype, parent_rn=None, ptype=None, empty_dim=False):
    f = client.get_type("AssetGroupListingGroupFilter")
    f.resource_name = rn
    f.asset_group = AG_RN
    if parent_rn:
        f.parent_listing_group_filter = parent_rn
    f.type_ = ftype
    f.listing_source = LS.SHOPPING
    if ptype:
        f.case_value.product_type.value = ptype
        f.case_value.product_type.level = LEVEL1
    elif empty_dim:
        f.case_value = client.get_type("ListingGroupFilterDimension")
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.create = f
    return op


dump_tree("建树前")

ops = [
    mk_create(PFX + "-1", ET.SUBDIVISION),                       # root 无 cv
    mk_create(PFX + "-2", ET.UNIT_INCLUDED, parent_rn=PFX + "-1",
              ptype="Medical Battery"),                          # medical 实值
    mk_create(PFX + "-3", ET.UNIT_EXCLUDED, parent_rn=PFX + "-1",
              empty_dim=True),                                   # else 空 cv
]
print("--- E3 单请求建树（root 无 cv + else 显式空 cv）---")
try:
    resp = svc.mutate_asset_group_listing_group_filters(
        customer_id=CID, operations=ops)
    for r in resp.results:
        print(f"  OK {r.resource_name}")
except Exception as e:  # noqa
    gerr = getattr(e, "failure", None)
    if gerr is not None:
        for er in gerr.errors:
            path = [fel.field_name for fel in
                    (er.location.field_path_elements or [])]
            print(f"  FAIL {er.error_code} msg={er.message!r} "
                  f"trigger={er.trigger!r} path={path}")
    else:
        print(f"  FAIL {str(e)[:500]}")
    raise SystemExit("E3 失败（原子回滚，维持空树）")

dump_tree("终态复核")
print("\n✔ 完成：商品池=product_type 'Medical Battery'，其余商品全部排除")
