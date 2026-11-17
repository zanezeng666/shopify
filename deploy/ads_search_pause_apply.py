# -*- coding: utf-8 -*-
"""批量 PAUSE 38 个非医疗 Search 系列（止血泛词流量），保留 Estry Medical Search。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.protobuf import field_mask_pb2

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

PAUSE_IDS = [
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
camp_service = gac.get_service("CampaignService")

CS = getattr(gac.enums.CampaignStatusEnum, "CampaignStatus",
             gac.enums.CampaignStatusEnum)

ops = []
for cid in PAUSE_IDS:
    op = gac.get_type("CampaignOperation")
    camp = op.update
    camp.resource_name = camp_service.campaign_path(CID, cid)
    camp.status = CS.PAUSED
    op.update_mask.CopyFrom(
        field_mask_pb2.FieldMask(paths=["status"]))
    ops.append(op)

resp = camp_service.mutate_campaigns(customer_id=CID, operations=ops)
print(f"已 PAUSE {len(resp.results)} 个系列")

# 验证：重查全部 SEARCH 系列
gas = gac.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.status "
    "FROM campaign WHERE campaign.advertising_channel_type = 'SEARCH'"))
en = paused = 0
for r in rows:
    st = r.campaign.status.name
    if st == "ENABLED":
        en += 1
        print(f"  仍在投: {r.campaign.name} ({r.campaign.id})")
    elif st == "PAUSED":
        paused += 1
print(f"\n验证完成：SEARCH 系列 ENABLED={en} PAUSED={paused}")
print("预期：仅剩 Estry Medical Search 在投")
