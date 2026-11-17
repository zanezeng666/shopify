# -*- coding: utf-8 -*-
"""修复二轮：
B2) PMax geo 兴趣漏斗：查 positive_geo_functionality，INTEREST→PRESENCE（只投实际在美的人）
A2) PMax Medical Estry 的 campaign_conversion_goal：非 PURCHASE 类全部 biddable=False
    （HIDDEN 动作改不了，但 goal 层是出价真正的开关）
"""
import os

from dotenv import load_dotenv
from google.protobuf import field_mask_pb2
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")


def q(sql):
    return list(gas.search(customer_id=CID, query=sql))


def step(tag, ok, msg=""):
    print(f"[{'OK' if ok else 'FAIL'}] {tag} {msg}")


CAMP_ID = 24441391608  # PMax Medical Estry

# ---------- B2) geo 兴趣定位 → 仅实际在场 ----------
print("== B2) positive_geo_functionality 检查与修复 ==")
try:
    r = q(f"SELECT campaign.name, campaign.geo_target_type_setting, "
          f"campaign.bidding_strategy_type FROM campaign "
          f"WHERE campaign.id = {CAMP_ID}")[0].campaign
    gts = r.geo_target_type_setting
    print(f"  campaign={r.name} 出价={r.bidding_strategy_type.name}")
    print(f"  positive={gts.positive_geo_functionality.name} "
          f"negative={gts.negative_geo_functionality.name}")
    if gts.positive_geo_functionality.name != "PRESENCE":
        cs = client.get_service("CampaignService")
        op = client.get_type("CampaignOperation")
        op.update.resource_name = f"customers/{CID}/campaigns/{CAMP_ID}"
        op.update.geo_target_type_setting.positive_geo_functionality = (
            client.get_type("GeoTargetingTypeEnum").GeoTargetingType.PRESENCE)
        op.update_mask.CopyFrom(field_mask_pb2.FieldMask(
            paths=["geo_target_type_setting.positive_geo_functionality"]))
        cs.mutate_campaigns(customer_id=CID, operations=[op])
        rb = q(f"SELECT campaign.geo_target_type_setting.positive_geo_functionality "
               f"FROM campaign WHERE campaign.id = {CAMP_ID}")[0].campaign
        step("B2", rb.geo_target_type_setting.positive_geo_functionuality.name
             == "PRESENCE",
             f"INTEREST→PRESENCE, readback="
             f"{rb.geo_target_type_setting.positive_geo_functionuality.name}")
    else:
        step("B2", True, "已是 PRESENCE（印度流量另有来源，需再查）")
except Exception as e:
    step("B2", False, repr(e)[:300])

# ---------- A2) campaign_conversion_goal 清洗 ----------
print("\n== A2) PMax conversion goals biddable 清洗 ==")
try:
    rows = q(f"SELECT campaign_conversion_goal.resource_name, "
             f"campaign_conversion_goal.category, "
             f"campaign_conversion_goal.origin, "
             f"campaign_conversion_goal.biddable "
             f"FROM campaign_conversion_goal WHERE campaign.id = {CAMP_ID}")
    cg = client.get_service("CampaignConversionGoalService")
    ops = []
    for r in rows:
        g = r.campaign_conversion_goal
        cat = g.category.name
        keep = cat in ("PURCHASE", "BEGIN_CHECKOUT")  # 电商主线保留
        mark = "留" if keep else "关"
        print(f"  {mark} [{cat:<18}|{g.origin.name:<12}] biddable={g.biddable}")
        if not keep and g.biddable:
            op = client.get_type("CampaignConversionGoalOperation")
            op.update.resource_name = g.resource_name
            op.update.biddable = False
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(
                paths=["biddable"]))
            ops.append(op)
    if ops:
        res = cg.mutate_campaign_conversion_goals(customer_id=CID, operations=ops)
        step("A2", len(res.results) == len(ops), f"关闭 {len(res.results)} 个非购买 goal")
    else:
        step("A2", True, "无需修改")
    print("  -- readback --")
    for r in q(f"SELECT campaign_conversion_goal.category, "
               f"campaign_conversion_goal.origin, campaign_conversion_goal.biddable "
               f"FROM campaign_conversion_goal WHERE campaign.id = {CAMP_ID}"):
        g = r.campaign_conversion_goal
        print(f"  [{g.category.name:<18}|{g.origin.name:<12}] biddable={g.biddable}")
except Exception as e:
    step("A2", False, repr(e)[:300])
