# -*- coding: utf-8 -*-
"""批量归档 bomibattery 时代 PAUSED 历史系列（status=REMOVED，可恢复）。"""
import os

from dotenv import load_dotenv
from google.protobuf import field_mask_pb2
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
ACTIVE = {24441391608, 24448362668}  # PMax Medical Estry / Estry Medical Search，永不触碰

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
cs = client.get_service("CampaignService")

# 1. 找出所有 PAUSED 历史系列（排除在投两个）
rows = list(gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.status "
    "FROM campaign WHERE campaign.status = 'PAUSED'")))
targets = [(r.campaign.id, r.campaign.name) for r in rows
           if r.campaign.id not in ACTIVE]
print(f"待归档 {len(targets)} 个 PAUSED 历史系列:")
for cid, name in targets:
    print(f"  {cid} | {name}")

# 2. 逐个构造归档操作（remove 即 status=REMOVED，v26 不允许 update 到 REMOVED）
ops = []
for cid, name in targets:
    op = client.get_type("CampaignOperation")
    op.remove = f"customers/{CID}/campaigns/{cid}"
    ops.append(op)

if ops:
    res = cs.mutate_campaigns(customer_id=CID, operations=ops)
    print(f"\n归档提交成功 {len(res.results)} 个")

# 3. readback：账户剩余非 REMOVED 系列
rows = list(gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.status "
    "FROM campaign WHERE campaign.status != 'REMOVED'")))
print(f"\nreadback：账户现存非归档系列 {len(rows)} 个")
for r in rows:
    print(f"  {r.campaign.id} | {r.campaign.name} | {r.campaign.status.name}")
