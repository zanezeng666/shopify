# -*- coding: utf-8 -*-
"""序列 E2：else 桶必须显式空 case_value（SetInParent）才被认作合法
everything-else 子节点。单请求原子换树，失败整请求回滚。
现状=root(custom 维度)+else(EXC)=零商品投放，需尽快换树。"""
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
ROOT = PFX + "15553272879"
ELSE_OLD = PFX + "15553272885"

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
    for r in gas.search(customer_id=CID, query=q_tree):
        f = r.asset_group_listing_group_filter
        print(f"  id={f.id} type={f.type_.name} src={f.listing_source.name} "
              f"ptype={f.case_value.product_type.value or '-'} "
              f"custom={f.case_value.product_custom_attribute.value or '-'}")


dump_tree("当前树")


def mk_create(rn, ftype, parent_rn=None, ptype=None):
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
    else:
        # 无维度节点（root / else 桶）必须显式占位空维度消息，
        # 否则 API 判 case_value REQUIRED 且不认 else 桶。
        f.case_value = client.get_type("ListingGroupFilterDimension")
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.create = f
    return op


def mk_remove(rn):
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.remove = rn
    return op


ops = [
    mk_remove(ELSE_OLD),
    mk_remove(ROOT),
    mk_create(PFX + "-1", ET.SUBDIVISION),
    mk_create(PFX + "-2", ET.UNIT_INCLUDED, parent_rn=PFX + "-1",
              ptype="Medical Battery"),
    mk_create(PFX + "-3", ET.UNIT_EXCLUDED, parent_rn=PFX + "-1"),
]
print("--- E2 单请求原子换树（5 ops，else/root 显式空 case_value）---")
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
    raise SystemExit("E2 失败（原子回滚，树维持 dump 所示状态）")

dump_tree("终态复核")
print("\n✔ 完成：商品池=product_type 'Medical Battery'，其余商品全部排除")
