# -*- coding: utf-8 -*-
"""修正方案：1) BROAD 词替换为同文本 PHRASE（match_type 不可变，remove+add）
2) 恢复 38 个系列 ENABLED。系列当前 PAUSED，改词期间无投放风险。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

RESUME_IDS = [
    24459062603, 24453830877, 24459059162, 24465005704, 24453835902,
    24465000205, 24453924126, 24459059711, 24464995678, 24465008068,
    24453845667, 24453834375, 24453834630, 24453839502, 24453847395,
    24453852894, 24453855279, 24453857427, 24453923931, 24453925410,
    24459034046, 24459035411, 24459036158, 24459036371, 24459048635,
    24459052487, 24459056312, 24459057491, 24459060713, 24459065021,
    24459066182, 24464983438, 24464990566, 24464992465, 24464996614,
    24465006367, 24465009973, 24465082978,
]

gac = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = gac.get_service("GoogleAdsService")
adc_service = gac.get_service("AdGroupCriterionService")
ag_service = gac.get_service("AdGroupService")
camp_service = gac.get_service("CampaignService")

CS = getattr(gac.enums.CampaignStatusEnum, "CampaignStatus",
             gac.enums.CampaignStatusEnum)
AGCS = getattr(gac.enums.AdGroupCriterionStatusEnum,
               "AdGroupCriterionStatus",
               gac.enums.AdGroupCriterionStatusEnum)
KM = getattr(gac.enums.KeywordMatchTypeEnum, "KeywordMatchTypeEnum",
             gac.enums.KeywordMatchTypeEnum)

# --- 拉全部 Estry Search 系列的关键词 ---
broad = []           # (agid, crit_id, text)
phrase_keys = set()  # (agid, text.lower()) 已存在的收紧词
rows = gas.search(customer_id=CID, query=(
    "SELECT ad_group.id, ad_group_criterion.criterion_id, "
    "ad_group_criterion.keyword.text, "
    "ad_group_criterion.keyword.match_type, "
    "ad_group_criterion.status "
    "FROM ad_group_criterion "
    "WHERE campaign.name LIKE 'Estry%Search%' "
    "AND campaign.status IN ('ENABLED', 'PAUSED') "
    "AND ad_group_criterion.type = 'KEYWORD' "
    "AND ad_group_criterion.status = 'ENABLED'"))
for r in rows:
    k = r.ad_group_criterion.keyword
    agid = r.ad_group.id
    crit = r.ad_group_criterion.criterion_id
    if k.match_type.name == "BROAD":
        broad.append((agid, crit, k.text))
    else:
        phrase_keys.add((agid, k.text.lower()))
print(f"BROAD 待替换 {len(broad)} 个，已存在收紧词 {len(phrase_keys)} 个")

# --- 分批 remove BROAD + add PHRASE ---
ops = []
skipped = 0
for agid, crit, text in broad:
    rop = gac.get_type("AdGroupCriterionOperation")
    rop.remove = adc_service.ad_group_criterion_path(CID, agid, crit)
    ops.append(rop)
    if (agid, text.lower()) not in phrase_keys:
        aop = gac.get_type("AdGroupCriterionOperation")
        adc = aop.create
        adc.ad_group = ag_service.ad_group_path(CID, agid)
        adc.keyword.text = text
        adc.keyword.match_type = KM.PHRASE
        adc.status = AGCS.ENABLED
        ops.append(aop)
        phrase_keys.add((agid, text.lower()))
    else:
        skipped += 1
print(f"操作总数 {len(ops)}（跳过重复 add {skipped} 个）")

done = 0
B = 2000
for i in range(0, len(ops), B):
    resp = adc_service.mutate_ad_group_criteria(
        customer_id=CID, operations=ops[i:i + B])
    n = len(resp.results)
    done += n
    pfe = resp.partial_failure_error
    if pfe:
        print(f"  批 {i//B+1}: 成功 {n}，部分失败: {str(pfe)[:200]}")
    else:
        print(f"  批 {i//B+1}: 成功 {n}")
print(f"关键词替换完成 {done} ops")

# --- 恢复 38 个系列 ---
cops = []
for cid in RESUME_IDS:
    op = gac.get_type("CampaignOperation")
    camp = op.update
    camp.resource_name = camp_service.campaign_path(CID, cid)
    camp.status = CS.ENABLED
    op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
    cops.append(op)
resp = camp_service.mutate_campaigns(customer_id=CID, operations=cops)
print(f"已恢复 ENABLED {len(resp.results)} 个系列")

# --- 验证 ---
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, campaign.status, "
    "ad_group_criterion.keyword.match_type "
    "FROM ad_group_criterion "
    "WHERE campaign.name LIKE 'Estry%Search%' "
    "AND campaign.status IN ('ENABLED', 'PAUSED') "
    "AND ad_group_criterion.type = 'KEYWORD' "
    "AND ad_group_criterion.status = 'ENABLED'"))
from collections import Counter
en, per_camp = 0, Counter()
rows2 = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, campaign.status FROM campaign "
    "WHERE campaign.advertising_channel_type = 'SEARCH' "
    "AND campaign.name LIKE 'Estry%'"))
camp_status = {}
for r in rows2:
    camp_status[r.campaign.name] = r.campaign.status.name
    if r.campaign.status.name == "ENABLED":
        en += 1
for r in rows:
    per_camp[r.ad_group_criterion.keyword.match_type.name] += 1
print(f"\n验证: Estry Search 系列在投 {en} 个")
print(f"验证: 词表匹配分布 {dict(per_camp)}")
print("预期: 39 个在投，BROAD=0")
