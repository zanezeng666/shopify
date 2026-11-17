# -*- coding: utf-8 -*-
"""精准化清理：删跨品类裸品牌词 + 暂停 Medical Generic 类目词组。

用户原则：刚需型号搜索截流，不做大词/消费推广。
- 删 4 词: Philips battery / GE battery (各 EXACT+PHRASE)——跨品类歧义
- 暂停组: Medical Generic（patient monitor battery 等 10 条类目大词）
- 保留: 纯医疗品牌词+设备系列词（无消费歧义的精准流量）
幂等：GAQL 查线上现状再操作，state 记录防重。
"""
import json
import os

from dotenv import load_dotenv
from google.protobuf import field_mask_pb2
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
STATE = f"{DEP}/ads_prune_broad.json"
CAMP = f"customers/{CID}/campaigns/24448362668"
DROP_WORDS = {"philips battery", "ge battery"}

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) \
    else {"removed": [], "paused_groups": []}

# ---- 1) 找 Medical Generic 组 ----
rows = gas.search(customer_id=CID, query=(
    "SELECT ad_group.resource_name, ad_group.name, ad_group.status "
    f"FROM ad_group WHERE ad_group.campaign='{CAMP}'"))
generic = None
groups = {}
for r in rows:
    groups[r.ad_group.resource_name] = r.ad_group.name
    if "generic" in r.ad_group.name.lower():
        generic = r.ad_group.resource_name
print(f"9 组: {len(groups)}; Medical Generic={generic}")

# ---- 2) 暂停 Generic 组 ----
if generic and generic not in state["paused_groups"]:
    ags = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    ag = op.update
    ag.resource_name = generic
    ag.status = client.enums.AdGroupStatusEnum.PAUSED
    op.update_mask.CopyFrom(
        field_mask_pb2.FieldMask(paths=["status"]))
    ags.mutate_ad_groups(customer_id=CID, operations=[op])
    state["paused_groups"].append(generic)
    json.dump(state, open(STATE, "w"), indent=1)
    print("paused: Medical Generic 组")
else:
    print("skip: Generic 组已暂停或不存在")

# ---- 3) 删跨品类裸品牌词 ----
if not state["removed"]:
    cksvc = client.get_service("AdGroupCriterionService")
    ops = []
    for ag_rn, ag_name in groups.items():
        kws = gas.search(customer_id=CID, query=(
            "SELECT ad_group_criterion.resource_name, "
            "ad_group_criterion.keyword.text, "
            "ad_group_criterion.keyword.match_type "
            f"FROM ad_group_criterion WHERE ad_group_criterion.ad_group="
            f"'{ag_rn}' AND ad_group_criterion.type='KEYWORD'"))
        for r in kws:
            t = r.ad_group_criterion.keyword.text.strip().lower()
            if t in DROP_WORDS:
                o = client.get_type("AdGroupCriterionOperation")
                o.remove = r.ad_group_criterion.resource_name
                ops.append((t, r.ad_group_criterion.keyword.match_type.name,
                            o))
    for t, m, o in ops:
        cksvc.mutate_ad_group_criteria(customer_id=CID, operations=[o])
        state["removed"].append(f"{t}({m})")
        print(f"removed: {t} ({m})")
    json.dump(state, open(STATE, "w"), indent=1)
else:
    print("skip: 已清理过", state["removed"])

# ---- 4) readback ----
n_kw = n_live_groups = 0
for ag_rn, ag_name in groups.items():
    st = list(gas.search(customer_id=CID, query=(
        "SELECT ad_group.status FROM ad_group "
        f"WHERE ad_group.resource_name='{ag_rn}'")))
    if not st or st[0].ad_group.status.name != "ENABLED":
        continue
    n_live_groups += 1
    kws = gas.search(customer_id=CID, query=(
        "SELECT ad_group_criterion.status FROM ad_group_criterion "
        f"WHERE ad_group_criterion.ad_group='{ag_rn}' "
        "AND ad_group_criterion.type='KEYWORD'"))
    n_kw += sum(1 for r in kws
                if r.ad_group_criterion.status.name == "ENABLED")
print(f"=== 清理后: 活跃组 {n_live_groups} / 活跃词 {n_kw} ===")
