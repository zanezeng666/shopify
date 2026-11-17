# -*- coding: utf-8 -*-
"""序列 F：分步探针建树。删旧树后逐节点单请求创建，
用响应里的真实 resource name 串联父子，排除临时 ID 悬空与
proto-plus 空 case_value presence 问题。每步失败打印细节。"""
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
    n = 0
    for r in gas.search(customer_id=CID, query=q_tree):
        f = r.asset_group_listing_group_filter
        print(f"  id={f.id} type={f.type_.name} src={f.listing_source.name} "
              f"ptype={f.case_value.product_type.value or '-'} "
              f"custom={f.case_value.product_custom_attribute.value or '-'}")
        n += 1
    if not n:
        print("  (空树：asset group 无 listing group filter)")
    return n


def submit(label, ops):
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


def mk_create(ftype, parent_rn=None, ptype=None, empty_dim=False):
    f = client.get_type("AssetGroupListingGroupFilter")
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


def mk_remove(rn):
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.remove = rn
    return op


# ---- 0. wire 探针：空 case_value 赋值是否序列化 ----
b_nocv = client.get_type("AssetGroupListingGroupFilter")
b_nocv.type_ = ET.UNIT_EXCLUDED
b_nocv.listing_source = LS.SHOPPING
probe = client.get_type("AssetGroupListingGroupFilter")
probe.case_value = client.get_type("ListingGroupFilterDimension")
probe.type_ = ET.UNIT_EXCLUDED
probe.listing_source = LS.SHOPPING
w_nocv = b_nocv._pb.SerializeToString()
w_cv = probe._pb.SerializeToString()
print("=== wire 探针：空 case_value 是否上 wire ===")
print(f"  不带 case_value: {len(w_nocv)}B {w_nocv!r}")
print(f"  带   case_value: {len(w_cv)}B {w_cv!r}")
print(f"  presence 生效: {w_cv != w_nocv}")

dump_tree("当前树")

# ---- 1. 删旧树（E2 已证明 remove else→remove root 序列可被接受）----
r1 = submit("F1 删旧树", [mk_remove(ELSE_OLD), mk_remove(ROOT)])
if r1 is None:
    raise SystemExit("F1 删除失败（原子回滚，树原样）")
dump_tree("删树后")

# ---- 2. 建 root（先不带 case_value，官方示例形态）----
r2 = submit("F2 create root SUBDIVISION（无 case_value）",
            [mk_create(ET.SUBDIVISION)])
if r2 is None:
    r2 = submit("F2b create root（带空 case_value）",
                [mk_create(ET.SUBDIVISION, empty_dim=True)])
if r2 is None:
    # 恢复：重建 root+else-EXC（还原零投放现状，可后台手工再修）
    rr = submit("F2 恢复 root", [mk_create(ET.SUBDIVISION)])
    if rr:
        submit("F2 恢复 else-EXC",
               [mk_create(ET.UNIT_EXCLUDED, parent_rn=rr[0], empty_dim=True)])
    raise SystemExit("F2 root 创建失败，已尝试恢复原状")
new_root = r2[0]

# ---- 3. 建 medical INC 桶 ----
r3 = submit("F3 create medical INC(product_type LEVEL1)",
            [mk_create(ET.UNIT_INCLUDED, parent_rn=new_root,
                       ptype="Medical Battery")])
if r3 is None:
    submit("F3 恢复 else-EXC", [mk_create(ET.UNIT_EXCLUDED,
                                          parent_rn=new_root,
                                          empty_dim=True)])
    raise SystemExit("F3 medical 桶失败，已恢复 root+else（全排除态）")

# ---- 4. 建 else-EXC（先带空 case_value）----
r4 = submit("F4 create else-EXC（空 case_value）",
            [mk_create(ET.UNIT_EXCLUDED, parent_rn=new_root,
                       empty_dim=True)])
if r4 is None:
    r4 = submit("F4b create else-EXC（不带 case_value）",
                [mk_create(ET.UNIT_EXCLUDED, parent_rn=new_root)])

dump_tree("终态复核")
print("\n✔ 完成：商品池=product_type 'Medical Battery'，其余商品全部排除")
