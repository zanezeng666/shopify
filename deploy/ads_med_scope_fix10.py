# -*- coding: utf-8 -*-
"""序列 G：proto 反射彻底查 ListingGroupFilterDimension 结构，
然后按组合变体建树（else 桶 = 同维度分支空值形态假设）。"""
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

# ---- proto 反射 ----
dim_cls = type(client.get_type("ListingGroupFilterDimension"))
print("=== ListingGroupFilterDimension oneofs/fields ===")
try:
    print(f"  oneofs: {list(dim_cls.meta.oneofs.keys())}")
except Exception as e:  # noqa
    print(f"  oneofs 查询失败: {e}")
for fname, fld in dim_cls.meta.fields.items():
    print(f"  field {fname}: {fld}")

for tname in ("ListingGroupFilterProductTypeInfo",
              "ListingGroupFilterProductLevelInfo"):
    try:
        pli = client.get_type(tname)
        print(f"=== {tname} 字段 ===")
        for fname in type(pli).meta.fields:
            print(f"  {fname}")
        break
    except ValueError:
        continue

# ---- wire 形态对照 ----
w_else_empty = client.get_type("AssetGroupListingGroupFilter")
w_else_empty.case_value = client.get_type("ListingGroupFilterDimension")
print(f"\nelse 空消息 wire: "
      f"{w_else_empty._pb.SerializeToString()!r}")

w_else_ptype_blank = client.get_type("AssetGroupListingGroupFilter")
w_else_ptype_blank.case_value.product_type.value = ""
print(f"else product_type='' wire: "
      f"{w_else_ptype_blank._pb.SerializeToString()!r}")

w_med = client.get_type("AssetGroupListingGroupFilter")
w_med.case_value.product_type.value = "Medical Battery"
w_med.case_value.product_type.level = LEVEL1
print(f"medical wire: {w_med._pb.SerializeToString()!r}")

q_tree = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.type, "
    "asset_group_listing_group_filter.listing_source, "
    "asset_group_listing_group_filter.case_value.product_type.value "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)


def dump_tree(title):
    print(f"=== {title} ===")
    n = 0
    for r in gas.search(customer_id=CID, query=q_tree):
        f = r.asset_group_listing_group_filter
        print(f"  id={f.id} type={f.type_.name} ptype="
              f"{f.case_value.product_type.value!r}")
        n += 1
    if not n:
        print("  (空树)")


def mk_create(rn, ftype, parent_rn=None, ptype=None, blank_ptype=False,
              with_level=False):
    f = client.get_type("AssetGroupListingGroupFilter")
    f.resource_name = rn
    f.asset_group = AG_RN
    if parent_rn:
        f.parent_listing_group_filter = parent_rn
    f.type_ = ftype
    f.listing_source = LS.SHOPPING
    if ptype is not None:
        f.case_value.product_type.value = ptype
        if with_level:
            f.case_value.product_type.level = LEVEL1
    elif blank_ptype:
        f.case_value.product_type.value = ""
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.create = f
    return op


def try_combo(label, ops):
    print(f"--- {label} ---")
    try:
        resp = svc.mutate_asset_group_listing_group_filters(
            customer_id=CID, operations=ops)
        for r in resp.results:
            print(f"  OK {r.resource_name}")
        return [r.resource_name for r in resp.results]
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
        return None


dump_tree("建树前")

root_op = lambda: mk_create(PFX + "-1", ET.SUBDIVISION)  # noqa: E731
med_op = lambda: mk_create(PFX + "-2", ET.UNIT_INCLUDED,  # noqa: E731
                           parent_rn=PFX + "-1",
                           ptype="Medical Battery", with_level=True)

combos = [
    ("G1 root无cv + medical实值 + else(ptype='')",
     [root_op(), med_op(),
      mk_create(PFX + "-3", ET.UNIT_EXCLUDED, parent_rn=PFX + "-1",
                blank_ptype=True)]),
    ("G2 else(ptype=''+level)",
     [root_op(), med_op(),
      mk_create(PFX + "-3", ET.UNIT_EXCLUDED, parent_rn=PFX + "-1",
                ptype="", with_level=True)]),
]
for label, ops in combos:
    r = try_combo(label, ops)
    if r:
        dump_tree("终态复核")
        print("\n✔ 完成：商品池=product_type 'Medical Battery'，"
              "其余商品全部排除")
        break
else:
    raise SystemExit("G 全部组合失败（各请求原子回滚，维持空树）")
