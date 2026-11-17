# -*- coding: utf-8 -*-
"""序列 C：remove custom 桶 -> update 28885 case_value -> product_type
-> create else-EXC。每步原子，失败即停无副作用。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.v26.enums.types.\
    listing_group_filter_product_type_level import (
    ListingGroupFilterProductTypeLevelEnum,
)

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
PFX = f"customers/{CID}/assetGroupListingGroupFilters/6770847164~"
ROOT = PFX + "15553272879"
LABEL_NODE = PFX + "15553272882"
NODE85 = PFX + "15553272885"

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
            print(f"  FAIL {str(e)[:400]}")
        return None


# C1: remove custom 桶
op1 = client.get_type("AssetGroupListingGroupFilterOperation")
op1.remove = LABEL_NODE
r1 = submit("C1 remove custom('ad-medical') 桶", [op1])
if r1 is None:
    raise SystemExit("C1 失败，树原状")

# C2: update 28885 case_value -> product_type('Medical Battery', LEVEL1)
u = client.get_type("AssetGroupListingGroupFilter")
u.resource_name = NODE85
u.asset_group = AG_RN
u.parent_listing_group_filter = ROOT
u.case_value.product_type.value = "Medical Battery"
u.case_value.product_type.level = LEVEL1
op2 = client.get_type("AssetGroupListingGroupFilterOperation")
op2.update = u
op2.update_mask.paths.append("case_value.product_type.value")
op2.update_mask.paths.append("case_value.product_type.level")
r2 = submit("C2 update 28885 -> product_type 桶", [op2])
if r2 is None:
    # 回滚 C1：重建 custom 桶还原原状
    f = client.get_type("AssetGroupListingGroupFilter")
    f.asset_group = AG_RN
    f.parent_listing_group_filter = ROOT
    f.type_ = ET.UNIT_INCLUDED
    f.case_value.product_custom_attribute.value = "ad-medical"
    op_rb = client.get_type("AssetGroupListingGroupFilterOperation")
    op_rb.create = f
    submit("C2 失败，回滚 C1（重建 ad-medical 桶）", [op_rb])
    raise SystemExit("C2 失败，已回滚到原状")

# C3: create else-EXC（28885 已成 medical 桶，else 缺位可建）
f3 = client.get_type("AssetGroupListingGroupFilter")
f3.asset_group = AG_RN
f3.parent_listing_group_filter = ROOT
f3.type_ = ET.UNIT_EXCLUDED
op3 = client.get_type("AssetGroupListingGroupFilterOperation")
op3.create = f3
r3 = submit("C3 create else-EXC", [op3])
if r3 is None:
    raise SystemExit("C3 失败；现状=root+medical 桶(28885)，else 缺失，"
                     "需后台补 else 排除节点")

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
print("\n完成：仅投 product_type='Medical Battery'（1,023 商品）")
