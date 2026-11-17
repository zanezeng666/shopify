# -*- coding: utf-8 -*-
"""零出单修复四连（诊断报告落地，2026-11-15）：
A) 转化动作清洗：3 个 HIDDEN+primary=True 的 engagement/page_view 动作降 primary=False
B) PMax Medical Estry geo 收窄 US only（删非 US 正定位，加 US=2840）
C) 3 个 TARGET_SPEND 策略 CPC 上限 ¥5 → ¥1.5
D) 否定词 SharedSet 挂全部 ENABLED Search campaign
E) GA4 generate_lead 标记 key event（Analytics Admin API）
F) 轮询 Ads 侧 generate_lead 转化动作 → 设 primary（同步延迟则如实报告）
"""
import os
import time

import httpx
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


# ---------- A) 转化动作清洗 ----------
print("\n== A) 转化动作 primary 清洗 ==")
DEMOTE = ["浏览超1分钟 (全部网站数据)", "智能目标 (全部网站数据)",
          "bomibattery - GA4 (web) Estry"]
try:
    rows = q("SELECT conversion_action.id, conversion_action.name, "
             "conversion_action.status, conversion_action.primary_for_goal "
             "FROM conversion_action")
    cas = client.get_service("ConversionActionService")
    ops = []
    for r in rows:
        ca = r.conversion_action
        if ca.name in DEMOTE and ca.primary_for_goal:
            op = client.get_type("ConversionActionOperation")
            op.update.resource_name = ca.resource_name
            op.update.primary_for_goal = False
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(
                paths=["primary_for_goal"]))
            ops.append(op)
            print(f"  待降级: {ca.name} (id={ca.id}, {ca.status.name})")
    if ops:
        res = cas.mutate_conversion_actions(customer_id=CID, operations=ops)
        step("A", len(res.results) == len(ops), f"降级 {len(res.results)} 个")
    else:
        step("A", True, "目标动作已全部 primary=False")
    for r in q("SELECT conversion_action.name, conversion_action.primary_for_goal "
               "FROM conversion_action"):
        if r.conversion_action.name in DEMOTE:
            print(f"  readback: {r.conversion_action.name} "
                  f"primary={r.conversion_action.primary_for_goal}")
except Exception as e:
    step("A", False, repr(e)[:200])

# ---------- B) PMax geo → US only ----------
print("\n== B) PMax Medical Estry geo 收窄 US ==")
try:
    camp = q("SELECT campaign.id, campaign.name FROM campaign "
             "WHERE campaign.name LIKE '%Medical Estry%' "
             "AND campaign.status = 'ENABLED'")[0].campaign
    pmc = f"customers/{CID}/campaigns/{camp.id}"
    print(f"  campaign: {camp.name} id={camp.id}")
    crits = q(f"SELECT campaign_criterion.resource_name, campaign_criterion.negative, "
              f"campaign_criterion.location.geo_target_constant "
              f"FROM campaign_criterion WHERE campaign.id = {camp.id} "
              f"AND campaign_criterion.type = 'LOCATION'")
    ccs = client.get_service("CampaignCriterionService")
    ops = []
    has_us = False
    for r in crits:
        cc = r.campaign_criterion
        geo = cc.location.geo_target_constant
        print(f"  现有{'负' if cc.negative else '正'}定位: {geo}")
        if not cc.negative:
            if geo.endswith("/2840"):
                has_us = True
            else:
                op = client.get_type("CampaignCriterionOperation")
                op.remove = cc.resource_name
                ops.append(op)
    if not has_us:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = pmc
        op.create.location.geo_target_constant = "geoTargetConstants/2840"
        ops.append(op)
    res = ccs.mutate_campaign_criteria(customer_id=CID, operations=ops)
    step("B", True, f"变更 {len(res.results)} 条 (删非US正定位+确保US在列)")
    for r in q(f"SELECT campaign_criterion.negative, "
               f"campaign_criterion.location.geo_target_constant "
               f"FROM campaign_criterion WHERE campaign.id = {camp.id} "
               f"AND campaign_criterion.type = 'LOCATION'"):
        print(f"  readback: {'负' if r.campaign_criterion.negative else '正'}"
              f" {r.campaign_criterion.location.geo_target_constant}")
except Exception as e:
    step("B", False, repr(e)[:300])

# ---------- C) CPC 上限回落 ----------
print("\n== C) TARGET_SPEND CPC 上限 ¥5→¥1.5 ==")
try:
    bss = client.get_service("BiddingStrategyService")
    n = 0
    for sid in (12308393566, 12310786752, 2049042622):
        rn = f"customers/{CID}/biddingStrategies/{sid}"
        op = client.get_type("BiddingStrategyOperation")
        op.update.resource_name = rn
        op.update.target_spend.cpc_bid_ceiling_micros = 1_500_000
        op.update_mask.CopyFrom(field_mask_pb2.FieldMask(
            paths=["target_spend.cpc_bid_ceiling_micros"]))
        bss.mutate_bidding_strategies(customer_id=CID, operations=[op])
        n += 1
        print(f"  策略 {sid} → ¥1.50")
    for r in q("SELECT bidding_strategy.id, "
               "bidding_strategy.target_spend.cpc_bid_ceiling_micros "
               "FROM bidding_strategy"):
        if r.bidding_strategy.id in (12308393566, 12310786752, 2049042622):
            print(f"  readback: {r.bidding_strategy.id} = "
                  f"¥{r.bidding_strategy.target_spend.cpc_bid_ceiling_micros/1e6:.2f}")
    step("C", n == 3, f"改 {n}/3")
except Exception as e:
    step("C", False, repr(e)[:300])

# ---------- D) 否定词 SharedSet ----------
print("\n== D) 否定词 SharedSet 挂 Search campaign ==")
NAV_JUNK = ["console games", "the game store", "www xbox", "playstation how much",
            "lamzu atlantis", "drag click mouse", "coros pace",
            "mouse wireless charging", "sound speaker"]
SS_NAME = "estry_nav_junk_20261115"
try:
    ss_set = client.get_type("SharedSet")
    type_field = "type_" if "type_" in ss_set._pb.DESCRIPTOR.fields_by_name else "type"
    existing = q(f"SELECT shared_set.id, shared_set.name FROM shared_set "
                 f"WHERE shared_set.name = '{SS_NAME}'")
    if existing:
        ss_rn = existing[0].shared_set.resource_name
        print(f"  复用现有 set: {ss_rn}")
    else:
        sss = client.get_service("SharedSetService")
        op = client.get_type("SharedSetOperation")
        setattr(op.create, "name", SS_NAME)
        setattr(op.create, type_field,
                client.get_type("SharedSetTypeEnum").SharedSetType.NEGATIVE_KEYWORDS)
        res = sss.mutate_shared_sets(customer_id=CID, operations=[op])
        ss_rn = res.results[0].resource_name
        print(f"  新建 set: {ss_rn}")
    have = {r.shared_criterion.keyword.text for r in q(
        f"SELECT shared_criterion.keyword.text FROM shared_criterion "
        f"WHERE shared_criterion.shared_set = '{ss_rn}'")}
    scs = client.get_service("SharedCriterionService")
    ops = []
    for w in NAV_JUNK:
        if w in have:
            continue
        op = client.get_type("SharedCriterionOperation")
        op.create.shared_set = ss_rn
        op.create.keyword.text = w
        op.create.keyword.match_type = client.get_type(
            "KeywordMatchTypeEnum").KeywordMatchType.PHRASE
        ops.append(op)
    if ops:
        scs.mutate_shared_criteria(customer_id=CID, operations=ops)
    print(f"  否定词就位 {len(NAV_JUNK)} 个 (已有 {len(have & set(NAV_JUNK))})")
    camps = q("SELECT campaign.id, campaign.name FROM campaign "
              "WHERE campaign.advertising_channel_type = 'SEARCH' "
              "AND campaign.status = 'ENABLED'")
    linked = {r.campaign_shared_set.campaign for r in q(
        f"SELECT campaign_shared_set.campaign FROM campaign_shared_set "
        f"WHERE campaign_shared_set.shared_set = '{ss_rn}'")}
    csss = client.get_service("CampaignSharedSetService")
    ops = []
    for r in camps:
        c_rn = r.campaign.resource_name
        if c_rn in linked:
            continue
        op = client.get_type("CampaignSharedSetOperation")
        op.create.campaign = c_rn
        op.create.shared_set = ss_rn
        ops.append(op)
    if ops:
        csss.mutate_campaign_shared_sets(customer_id=CID, operations=ops)
    step("D", True, f"挂载 {len(camps)} 个 Search campaign (新关联 {len(ops)})")
except Exception as e:
    step("D", False, repr(e)[:300])

# ---------- E) GA4 generate_lead → key event ----------
print("\n== E) GA4 generate_lead 标记 key event ==")
try:
    tok = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
    ah = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    base = "https://analyticsadmin.googleapis.com/v1beta/properties/313397200"
    r = httpx.get(f"{base}/keyEvents", headers=ah, timeout=30)
    names = {k["eventName"] for k in r.json().get("keyEvents", [])}
    print(f"  现有 key events: {sorted(names)}")
    if "generate_lead" in names:
        step("E", True, "已是 key event")
    else:
        r2 = httpx.post(f"{base}/keyEvents", headers=ah,
                        json={"eventName": "generate_lead"}, timeout=30)
        step("E", r2.status_code == 200, f"POST {r2.status_code} {r2.text[:120]}")
except Exception as e:
    step("E", False, repr(e)[:200])

# ---------- F) Ads 侧 generate_lead 动作 → primary ----------
print("\n== F) Ads generate_lead 转化动作设 primary（轮询 GA4 同步） ==")
try:
    found = None
    for i in range(6):
        rows = q("SELECT conversion_action.id, conversion_action.name, "
                 "conversion_action.status, conversion_action.primary_for_goal "
                 "FROM conversion_action WHERE conversion_action.name "
                 "LIKE '%generate%'")
        if rows:
            found = rows[0].conversion_action
            break
        print(f"  第 {i+1} 轮未见同步，等 20s...")
        time.sleep(20)
    if not found:
        step("F", False, "GA4→Ads 同步未完成（正常，分钟~小时级），稍后复查")
    else:
        print(f"  找到: {found.name} id={found.id} {found.status.name} "
              f"primary={found.primary_for_goal}")
        if not found.primary_for_goal:
            cas = client.get_service("ConversionActionService")
            op = client.get_type("ConversionActionOperation")
            op.update.resource_name = found.resource_name
            op.update.primary_for_goal = True
            op.update_mask.CopyFrom(field_mask_pb2.FieldMask(
                paths=["primary_for_goal"]))
            cas.mutate_conversion_actions(customer_id=CID, operations=[op])
        step("F", True, "primary=True 已确保")
except Exception as e:
    step("F", False, repr(e)[:200])

print("\n== 全部完成 ==")
