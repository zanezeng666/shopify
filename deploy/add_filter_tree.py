# -*- coding: utf-8 -*-
"""用 gRPC google-ads 客户端建 listing_group_filter 树.

绕开 REST 网关对临时负ID的 BAD_RESOURCE_ID 限制 (gRPC 通道是官方支持的临时ID用法).
树: SUBDIVISION root -> UNIT_INCLUDED(custom_attribute0=ad-medical, 842品)
                       + UNIT_EXCLUDED(其余全部排除)
成功后把 root resource name 写进 pmax_created.json (filter_root + filter_done).
"""
import json
import os
import sys

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
STATE = f"{DEP}/pmax_created.json"

state = json.load(open(STATE, encoding="utf-8"))
AG = state["asset_group"]
if not AG:
    sys.exit("asset_group missing in state")

creds = {
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "developer_token": os.environ.get("GOOGLE_DEVELOPER_TOKEN", "unused"),
    "use_proto_plus": True,
}
client = GoogleAdsClient.load_from_dict(creds)
svc = client.get_service("GoogleAdsService")

# 服务端错误信息明确格式: customers/{cid}/assetGroupListingGroupFilters/{agid}~{fid}
# 临时名 = agid~-1
AGID = AG.rsplit("/", 1)[-1]
tmp_root = f"customers/{CID}/assetGroupListingGroupFilters/{AGID}~-1"

FT = client.enums.ListingGroupFilterTypeEnum
LS = client.enums.ListingGroupFilterListingSourceEnum

ops = []

root_op = client.get_type("MutateOperation")
f = root_op.asset_group_listing_group_filter_operation.create
f.resource_name = tmp_root
f.asset_group = AG
f.type_ = FT.SUBDIVISION
f.listing_source = LS.SHOPPING
ops.append(root_op)

inc_op = client.get_type("MutateOperation")
f = inc_op.asset_group_listing_group_filter_operation.create
f.asset_group = AG
f.type_ = FT.UNIT_INCLUDED
f.listing_source = LS.SHOPPING
f.parent_listing_group_filter = tmp_root
# 注意: case_value.product_custom_attribute.index 用的是
# ListingGroupFilterCustomAttributeIndex 枚举 (INDEX0=2),
# 不是 ProductCustomAttributeIndex (INDEX0=7, 用于 campaign_criterion)
IDX = client.enums.ListingGroupFilterCustomAttributeIndexEnum
attr = f.case_value.product_custom_attribute
attr.value = "ad-medical"
attr.index = IDX.INDEX0
ops.append(inc_op)

exc_op = client.get_type("MutateOperation")
f = exc_op.asset_group_listing_group_filter_operation.create
f.asset_group = AG
f.type_ = FT.UNIT_EXCLUDED
f.listing_source = LS.SHOPPING
f.parent_listing_group_filter = tmp_root
# everything else: 同维度 index, value 留空
attr = f.case_value.product_custom_attribute
attr.index = IDX.INDEX0
ops.append(exc_op)

try:
    resp = svc.mutate(customer_id=CID, mutate_operations=ops)
except Exception as ex:
    from google.ads.googleads.errors import GoogleAdsException
    if isinstance(ex, GoogleAdsException):
        for e in ex.failure.errors:
            print("ERR:", e.message.encode("utf-8", "replace").decode("utf-8"))
            print("  path:",
                  [p.field_name for p in e.location.field_path_elements],
                  "trigger:", e.trigger)
    raise SystemExit(1)
root_res = (resp.mutate_operation_responses[0]
            .asset_group_listing_group_filter_result.resource_name)
print("root:", root_res)
for r in resp.mutate_operation_responses[1:]:
    print("child:", r.asset_group_listing_group_filter_result.resource_name)

state["filter_root"] = root_res
state["filter_done"] = True
with open(STATE, "w", encoding="utf-8") as fh:
    json.dump(state, fh, indent=1, ensure_ascii=False)
print("state saved")
