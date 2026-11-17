# -*- coding: utf-8 -*-
"""序列 D v2：listing_source 与现有节点对齐（查询读出后直接用）。"""
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
AG_RN = f"customers/{CID}/assetGroups/6770847164"
PFX = f"customers/{CID}/assetGroupListingGroupFilters/6770847164~"
ROOT = PFX + "15553272879"
ELSE_INC = PFX + "15553272885"

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
    "asset_group_listing_group_filter.listing_source, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "value "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)

print("=== 当前树（含 listing_source）===")
cur_src = None
for r in gas.search(customer_id=CID, query=q_tree):
    f = r.asset_group_listing_group_filter
    print(f"  id={f.id} src={f.listing_source.name} "
          f"ptype={f.case_value.product_type.value or '-'} "
          f"custom={f.case_value.product_custom_attribute.value or '-'}")
    cur_src = f.listing_source
SRC = {"SHOPPING": LS.SHOPPING, "WEBPAGE": LS.WEBPAGE,
       "RETAIL": LS.RETAIL}.get(cur_src.name, LS.SHOPPING)
print(f"新建节点将用 listing_source={SRC}")


def submit(label, ops):
    print(f"--- {label} ---")
    try:
        resp = svc.mutate_asset_group_listing_group_filters(
            customer_id=CID, operations=ops)
        for r in resp.results:
            print(f"  OK {r.resource_name}")
        return list(resp.results)
    except Exception as e:  # noqa
        gerr = getattr(e, "failure", None)
        if gerr is not None:
            for er in gerr.errors:
                path = [fel.field_name for fel in
                        (er.location.field_path_elements or [])]
                print(f"  FAIL {er.error_code} msg={er.message!r} "
                      f"trigger={er.trigger!r} path={path}")
        else:
            print(f"  FAIL {str(e)[:400]}")
        return None


def mk_create(parent_rn, ftype, ptype=None):
    f = client.get_type("AssetGroupListingGroupFilter")
    f.asset_group = AG_RN
    f.parent_listing_group_filter = parent_rn
    f.type_ = ftype
    f.listing_source = SRC
    if ptype:
        f.case_value.product_type.value = ptype
        f.case_value.product_type.level = LEVEL1
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.create = f
    return op


r1 = submit("D1 create medical(product_type) INC",
            [mk_create(ROOT, ET.UNIT_INCLUDED, ptype="Medical Battery")])
if r1 is None:
    raise SystemExit("D1 失败；树维持 root+else(全投)")

r2 = submit("D2 create else-EXC", [mk_create(ROOT, ET.UNIT_EXCLUDED)])
if r2 is None:
    raise SystemExit("D2 失败；现状=root+medical(INC)+else-INC；"
                     "后台手工：商品组->其他所有产品->改为排除")

op3 = client.get_type("AssetGroupListingGroupFilterOperation")
op3.remove = ELSE_INC
r3 = submit("D3 remove 旧 else-INC", [op3])
if r3 is None:
    raise SystemExit("D3 失败；现状=medical(INC)+else 双存；"
                     "后台手工删除 INC-else 节点")

print("\n=== 终态复核 ===")
for r in gas.search(customer_id=CID, query=q_tree):
    f = r.asset_group_listing_group_filter
    print(f"  id={f.id} src={f.listing_source.name} "
          f"ptype={f.case_value.product_type.value or '-'} "
          f"custom={f.case_value.product_custom_attribute.value or '-'}")
print("\n✔ 完成：商品池=product_type 'Medical Battery'，其他全部排除")
