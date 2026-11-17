# -*- coding: utf-8 -*-
"""PMax listing 收敛为 Medical Battery 类。
单次原子批量：remove 2 个空子节点 + create [INCLUDED product_type='Medical
Battery'] + [EXCLUDED 其他所有产品]。失败自动中止不落半态。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
AG_RN = f"customers/{CID}/assetGroups/6770847164"
ROOT_RN = (f"customers/{CID}/assetGroupListingGroupFilters/"
           "6770847164~15553272879")
OLD_CHILDREN = [
    f"customers/{CID}/assetGroupListingGroupFilters/6770847164~15553272882",
    f"customers/{CID}/assetGroupListingGroupFilters/6770847164~15553272885",
]

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})

enum = client.get_type("ListingGroupFilterTypeEnum").ListingGroupFilterType
names = [n for n in dir(enum) if not n.startswith("_")]
print(f"枚举值: {names}")
INC = enum.UNIT_INCLUDED
EXC = enum.UNIT_EXCLUDED
print(f"UNIT_INCLUDED={INC} UNIT_EXCLUDED={EXC}")

svc = client.get_service("AssetGroupListingGroupFilterService")

ops = []
for rn in OLD_CHILDREN:
    op = client.get_type("AssetGroupListingGroupFilterOperation")
    op.remove = rn
    ops.append(op)

f_inc = client.get_type("AssetGroupListingGroupFilter")
f_inc.asset_group = AG_RN
f_inc.parent_listing_group_filter = ROOT_RN
f_inc.type_ = INC
f_inc.case_value.product_type.value = "Medical Battery"
op_inc = client.get_type("AssetGroupListingGroupFilterOperation")
op_inc.create = f_inc
ops.append(op_inc)

f_exc = client.get_type("AssetGroupListingGroupFilter")
f_exc.asset_group = AG_RN
f_exc.parent_listing_group_filter = ROOT_RN
f_exc.type_ = EXC
op_exc = client.get_type("AssetGroupListingGroupFilterOperation")
op_exc.create = f_exc
ops.append(op_exc)

print("\n提交批量 mutate（2 remove + 2 create）...")
try:
    resp = svc.mutate_asset_group_listing_group_filters(
        customer_id=CID, operations=ops)
    for r in resp.results:
        print(f"  OK {r.resource_name}")
except Exception as e:  # noqa
    print(f"  MUTATE 失败: {str(e)[:800]}")
    raise SystemExit(1)

print("\n=== 复核：新树 ===")
gas = client.get_service("GoogleAdsService")
q = (
    "SELECT asset_group_listing_group_filter.id, "
    "asset_group_listing_group_filter.parent_listing_group_filter, "
    "asset_group_listing_group_filter.case_value.product_type.value "
    f"FROM asset_group_listing_group_filter WHERE campaign.id = 24441391608"
)
for r in gas.search(customer_id=CID, query=q):
    f = r.asset_group_listing_group_filter
    par = f.parent_listing_group_filter or "(根)"
    print(f"  id={f.id} parent={'根' if par == '(根)' else par.split('~')[-1]} "
          f"ptype={f.case_value.product_type.value or '(空=其他全部)'}")
print("\n完成：PMax 投放范围已收敛为 product_type='Medical Battery'")
