# -*- coding: utf-8 -*-
"""PMax 医疗收敛 v3：阶梯策略逐请求执行。
T1 update 28882: case_value -> product_type='Medical Battery'
T2 create else-EXC（与现有 INC-else 并存试探）
T3 remove 28885(INC-else) -> 终态 root+medical(INC)+else(EXC)
T4 兜底：remove root 整树 -> 重建 root(SUBDIV)+medical(INC)+else(EXC)
"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
PFX = f"customers/{CID}/assetGroupListingGroupFilters/6770847164~"

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
ET = client.get_type("ListingGroupFilterTypeEnum").ListingGroupFilterType
# product_type.level 必填：LEVEL1=2（feed 第一层级值）
from google.ads.googleads.v26.enums.types.\
    listing_group_filter_product_type_level import (
    ListingGroupFilterProductTypeLevelEnum,
)
LEVEL1 = (ListingGroupFilterProductTypeLevelEnum
          .ListingGroupFilterProductTypeLevel.LEVEL1)
print(f"level = {LEVEL1}")
svc = client.get_service("AssetGroupListingGroupFilterService")


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
            print(f"  FAIL {str(e)[:600]}")
        return None


def mk_update(rn, mask, **fields):
    u = client.get_type("AssetGroupListingGroupFilter")
    u.resource_name = rn
    u.asset_group = AG_RN
    u.parent_listing_group_filter = ROOT
    u.type_ = ET.UNIT_INCLUDED
    ls_enum = (client.get_type("ListingGroupFilterListingSourceEnum")
               .ListingGroupFilterListingSource)
    for cand in ("PARTNER", "SHOPPING", "MERCHANT_CENTER", "WEBSITE"):
        if hasattr(ls_enum, cand):
            u.listing_source = getattr(ls_enum, cand)
            break
    if "ptype" in fields:
        u.case_value.product_type.value = fields["ptype"]
        if LEVEL1 is not None:
            u.case_value.product_type.level = LEVEL1
    if "ftype" in fields:
        u.type_ = fields["ftype"]
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.update = u
    for m in mask.split(","):
        op.update_mask.paths.append(m)
    return op


def mk_create(parent_rn, ftype, ptype=None):
    f = client.get_type("AssetGroupListingGroupFilter")
    f.asset_group = AG_RN
    f.parent_listing_group_filter = parent_rn
    f.type_ = ftype
    if ptype:
        f.case_value.product_type.value = ptype
        if LEVEL1 is not None:
            f.case_value.product_type.level = LEVEL1
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.create = f
    return op


ROOT = PFX + "15553272879"
LABEL_NODE = PFX + "15553272882"
ELSE_INC = PFX + "15553272885"

# T1: 换维度（已证会撞兄弟维度约束，保留尝试）
r1 = submit("T1 label桶->product_type桶",
            [mk_update(LABEL_NODE,
                       "case_value.product_type.value,"
                       "case_value.product_type.level",
                       ptype="Medical Battery")])

r2 = None
if r1 is not None:
    # T2: create EXC else（并存试探）
    r2 = submit("T2 create else-EXC", [mk_create(ROOT, ET.UNIT_EXCLUDED)])

if r1 is None or r2 is None:
    print(">>> 进入 T4 整树重建路径")
    # T4a: remove root（级联删 custom 桶 + INC-else）
    op_rm = client.get_type("AssetGroupListingGroupFilterOperation")
    op_rm.remove = ROOT
    r4a = submit("T4a remove root 整树", [op_rm])
    if r4a is None:
        raise SystemExit("T4a 失败；树保持原状（custom 桶+INC-else 全投），"
                         "需手工后台处理")
    # T4b: create 新 root SUBDIVISION
    f = client.get_type("AssetGroupListingGroupFilter")
    f.asset_group = AG_RN
    f.type_ = ET.SUBDIVISION
    op_c = client.get_type("AssetGroupListingGroupFilterOperation")
    op_c.create = f
    r4b = submit("T4b create root SUBDIVISION", [op_c])
    if r4b is None:
        raise SystemExit("T4b 失败！树为空，需立即手工后台重建商品组")
    new_root = r4b[0].resource_name
    r4c = submit("T4c create medical(INC)+else(EXC)",
                 [mk_create(new_root, ET.UNIT_INCLUDED,
                            ptype="Medical Battery"),
                  mk_create(new_root, ET.UNIT_EXCLUDED)])
    if r4c is None:
        raise SystemExit("T4c 失败！树仅 root，需手工补子节点")
else:
    # T3: remove 旧 INC-else
    op3 = client.get_type("AssetGroupListingGroupFilterOperation")
    op3.remove = ELSE_INC
    r3 = submit("T3 remove 旧 INC-else", [op3])
    if r3 is None:
        raise SystemExit("T3 失败；现状=medical(INC)+else-INC+else-EXC 并存，"
                         "请后台手工删 INC-else")

print("\n=== 终态复核 ===")
gas = client.get_service("GoogleAdsService")
q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.parent_listing_group_filter, "
    "asset_group_listing_group_filter.case_value.product_type.value, "
    "asset_group_listing_group_filter.case_value.product_custom_attribute."
    "value "
    "FROM asset_group_listing_group_filter "
    "WHERE campaign.id = 24441391608"
)
for r in gas.search(customer_id=CID, query=q):
    f = r.asset_group_listing_group_filter
    par = f.parent_listing_group_filter
    print(f"  id={f.id} parent={'(根)' if not par else par.split('~')[-1]} "
          f"ptype={f.case_value.product_type.value or '-'} "
          f"custom={f.case_value.product_custom_attribute.value or '-'}")
