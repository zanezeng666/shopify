# -*- coding: utf-8 -*-
"""创建 Search 广告系列「Estry Medical Search」。

输入: deploy/med_search_keywords.json（mine_medical_keywords.py 产出）
预算 $15/天 | US+英语 | Maximize Clicks(出价上限$1.5) | RSA 文字广告
结构: budget -> campaign(PAUSED) -> 定向/负词 -> callouts -> ad_groups ->
      keywords(分块) -> RSA -> ENABLE -> readback
断点: deploy/med_search_created.json（幂等重跑）
"""
import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
DEP = "/home/jason/shopify-admin/deploy"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
PLAN = f"{DEP}/med_search_keywords.json"
STATE = f"{DEP}/med_search_created.json"
BUDGET_USD = 15.0
CPC_CEILING = 1_500_000  # $1.50

plan = json.load(open(PLAN, encoding="utf-8"))
state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
for k in ("budget", "campaign", "criteria", "callouts", "keywords",
          "ads", "enabled"):
    state.setdefault(k, None if k != "enabled" else False)
state.setdefault("adgroups", {})


def token():
    return httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


H = {"Content-Type": "application/json", "developer-token": "unused"}


def mutate(res, operations, op="create", label=""):
    if op == "create":
        body = {"operations": [{op: o} for o in operations]}
    else:  # operations 已是完整操作对象（含 update/updateMask 键）
        body = {"operations": operations}
    r = httpx.post(f"{API}/{res}:mutate",
                   headers={**H, "Authorization": f"Bearer {token()}"},
                   json=body, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"{label}: HTTP{r.status_code} FULL={r.text[:3200]}")
    return [x.get("resourceName", "") for x in r.json().get("results", [])]


def query(gaql):
    r = httpx.post(f"{API}/googleAds:search",
                   headers={**H, "Authorization": f"Bearer {token()}"},
                   json={"query": gaql}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GAQL HTTP{r.status_code}: {r.text[:500]}\n"
                           f"GAQL: {gaql[:200]}")
    return r.json().get("rows") or r.json().get("results") or []


def save():
    json.dump(state, open(STATE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


# ---------- 0: 前置校验 + 重名检查 ----------
SHARED_HEADS = [
    "Medical Device Batteries",   # 24
    "Patient Monitor Battery",    # 23
    "Defibrillator Battery",      # 21
    "1-Year Warranty, Exact Fit",  # 26
    "Ships From US Warehouse",    # 23
    "Check Your Device Model",    # 23
    "Estry Medical Batteries",    # 23
    "Order Online, Fast Shipping",  # 27
    "Ventilator & ECG Batteries",  # 26
    "For Repair & Biomed Teams",  # 26
]
SHARED_DESCS = [
    "Replacement batteries for patient monitors, defibrillators & devices.",
    "Exact fit for your device model. US stock, fast shipping, 1-yr warranty.",
    "High-capacity replacement batteries for medical equipment. Order online.",
    "Browse compatible batteries by brand and model. Ships from US warehouse.",
]


def brand_heads(b: str) -> list[str]:
    if b == "Medical Generic":
        cands = ["Medical Battery Replacement", "OEM-Fit Medical Batteries"]
    else:
        cands = [f"Batteries for {b}", f"{b} Battery Replacement",
                 f"{b} Batteries"]
    return [c for c in cands if len(c) <= 30][:2]


def validate() -> None:
    problems = []
    for h in SHARED_HEADS:
        if len(h) > 30:
            problems.append(f"headline>30: {h}")
    for d in SHARED_DESCS:
        if len(d) > 90:
            problems.append(f"desc>90: {d}")
    for g in plan["ad_groups"]:
        for h in brand_heads(g["name"]):
            if len(h) > 30:
                problems.append(f"{g['name']} headline>30: {h}")
        for k in g["keywords"]:
            if len(k["text"]) > 80:
                problems.append(f"{g['name']} kw>80: {k['text']}")
    for k in plan["negatives"]:
        if len(k["text"]) > 80:
            problems.append(f"neg>80: {k['text']}")
    if problems:
        raise SystemExit("文案校验失败:\n" + "\n".join(problems))
    print(f"文案校验过: {len(plan['ad_groups'])} 组, "
          f"{sum(len(g['keywords']) for g in plan['ad_groups'])} 词")


def main() -> None:
    validate()
    name = plan["campaign_name"]
    dup = query(f"SELECT campaign.resource_name, campaign.status FROM campaign "
                f"WHERE campaign.name='{name}'")
    if dup and not state["campaign"]:
        raise SystemExit(f"同名 campaign 已存在: {dup}")
    if dup:
        print("警告: 同名存在，按断点续跑")

    # ---------- 1: budget ----------
    if not state["budget"]:
        state["budget"] = mutate("campaignBudgets", [{
            "name": f"Budget {name}",
            "amountMicros": str(int(BUDGET_USD * 1_000_000)),
            "explicitlyShared": False,
            "deliveryMethod": "STANDARD"}], label="budget")[0]
        save()
    print("budget:", state["budget"])

    # ---------- 2: 组合出价策略（v25 Campaign 已无 maximizeClicks 字段） ----------
    if not state.get("bidding"):
        state["bidding"] = mutate("biddingStrategies", [{
            "name": "MaxClicks Estry Medical cap150",
            "targetSpend": {"cpcBidCeilingMicros": str(CPC_CEILING)},
        }], label="bidding")[0]
        save()
    print("bidding:", state["bidding"])

    # ---------- 3: campaign (PAUSED) ----------
    if not state["campaign"]:
        state["campaign"] = mutate("campaigns", [{
            "name": name,
            "status": "PAUSED",
            "advertisingChannelType": "SEARCH",
            "campaignBudget": state["budget"],
            "biddingStrategy": state["bidding"],
            "networkSettings": {
                "targetGoogleSearch": True,
                "targetSearchNetwork": False,
                "targetPartnerSearchNetwork": False,
                "targetContentNetwork": False},
            "containsEuPoliticalAdvertising":
                "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
        }], label="campaign")[0]
        save()
    CAMP = state["campaign"]
    print("campaign:", CAMP)

    # ---------- 3: 语言/地域/负词 ----------
    if not state["criteria"]:
        camp_id = CAMP.split("/")[-1]
        rn = lambda cid: f"customers/{CID}/campaignCriteria/{camp_id}~{cid}"
        ops = [
            {"resourceName": rn("1000"), "campaign": CAMP,
             "criterionId": "1000", "language": {}},   # English
            {"resourceName": rn("2840"), "campaign": CAMP,
             "criterionId": "2840", "location": {}},   # United States
        ]
        for k in plan["negatives"]:
            ops.append({"campaign": CAMP, "negative": True,
                        "keyword": {"text": k["text"],
                                    "matchType": k["match"]}})
        mutate("campaignCriteria", ops, label="criteria")
        state["criteria"] = True
        save()
    print("criteria ok")

    # ---------- 4: callout 资产 ----------
    if not state["callouts"]:
        texts = ["US Stock", "Fast US Shipping", "1-Year Warranty",
                 "Check Model Fit"]
        existing = {}
        for row in query("SELECT asset.resource_name, "
                         "asset.callout_asset.callout_text FROM asset "
                         "WHERE asset.type='CALLOUT'"):
            a = row.get("asset", {})
            t = (a.get("calloutAsset") or {}).get("calloutText")
            if t:
                existing[t] = a["resourceName"]
        names = [existing[t] for t in texts if t in existing]
        missing = [t for t in texts if t not in existing]
        if missing:
            names += mutate("assets",
                            [{"calloutAsset": {"calloutText": t}}
                             for t in missing], label="callouts")
        mutate("campaignAssets", [
            {"asset": a, "campaign": CAMP, "fieldType": "CALLOUT"}
            for a in names], label="link_callouts")
        state["callouts"] = True
        save()
    print("callouts ok")

    # ---------- 5: ad_groups ----------
    todo = [g for g in plan["ad_groups"] if g["name"] not in state["adgroups"]]
    if todo:
        ops = [{"name": g["name"], "campaign": CAMP,
                "status": "ENABLED", "type": "SEARCH_STANDARD",
                "cpcBidMicros": "1000000"} for g in todo]
        rns = mutate("adGroups", ops, label="adgroups")
        for g, rn in zip(todo, rns):
            state["adgroups"][g["name"]] = rn
        save()
    print("ad_groups:", len(state["adgroups"]))

    # ---------- 6: keywords（分块，幂等去重） ----------
    if not isinstance(state["keywords"], int):
        have = set()
        for g0 in plan["ad_groups"]:
            ag0 = state["adgroups"][g0["name"]]
            for row in query(
                    "SELECT ad_group_criterion.keyword.text, "
                    "ad_group_criterion.keyword.match_type "
                    "FROM ad_group_criterion "
                    f"WHERE ad_group_criterion.ad_group='{ag0}' "
                    "AND ad_group_criterion.type='KEYWORD'"):
                c = row.get("adGroupCriterion", {})
                k = c.get("keyword", {})
                if k.get("text"):
                    have.add((ag0, k.get("text"), k.get("matchType")))
        ops = []
        skipped = 0
        for g in plan["ad_groups"]:
            ag = state["adgroups"][g["name"]]
            for k in g["keywords"]:
                if (ag, k["text"], k["match"]) in have:
                    skipped += 1
                    continue
                ops.append({"adGroup": ag,
                            "keyword": {"text": k["text"],
                                        "matchType": k["match"]}})
        print(f"待建关键词 {len(ops)} / 已存在跳过 {skipped}")
        done = 0
        for i in range(0, len(ops), 100):
            mutate("adGroupCriteria", ops[i:i + 100],
                   label=f"keywords[{i}:{i + 100}]")
            done += len(ops[i:i + 100])
            state["keywords"] = f"进行中 {done}"
            save()
        state["keywords"] = len(ops) + skipped
        save()
    print("keywords:", state["keywords"])

    # ---------- 7: RSA 文字广告 ----------
    if not state["ads"]:
        for g in plan["ad_groups"]:
            ag = state["adgroups"][g["name"]]
            heads = brand_heads(g["name"]) + SHARED_HEADS
            descs = SHARED_DESCS
            mutate("adGroupAds", [{
                "adGroup": ag, "status": "ENABLED",
                "ad": {
                    "responsiveSearchAd": {
                        "headlines": [{"text": t} for t in heads],
                        "descriptions": [{"text": t} for t in descs],
                        "path1": "medical-battery",
                        "path2": "replacement"},
                    "finalUrls": [plan["url"]]}}], label=f"rsa[{g['name']}]")
        state["ads"] = True
        save()
    print("ads ok")

    # ---------- 8: ENABLE ----------
    if not state["enabled"]:
        mutate("campaigns", [{
            "update": {"resourceName": CAMP, "status": "ENABLED"},
            "updateMask": "status"}], op="update", label="enable")
        state["enabled"] = True
        save()

    # ---------- 9: readback ----------
    print("\n=== readback ===")
    for row in query(
        f"SELECT campaign.name, campaign.status, campaign.bidding_strategy_type "
        f"FROM campaign WHERE campaign.resource_name='{CAMP}'"):
        c = row.get("campaign", {})
        print(f"campaign: {c.get('name')} {c.get('status')} "
              f"{c.get('biddingStrategyType')}")
    ags = query(
        f"SELECT ad_group.name, ad_group.status FROM ad_group "
        f"WHERE ad_group.campaign='{CAMP}'")
    print(f"ad_groups live: {len(ags)}")
    for row in ags:
        a = row.get("adGroup", {})
        print(f"  [{a.get('status')}] {a.get('name')}")
    kw_total = 0
    for g0 in plan["ad_groups"]:
        ag0 = state["adgroups"][g0["name"]]
        kw_total += len(query(
            "SELECT ad_group_criterion.keyword.text FROM ad_group_criterion "
            f"WHERE ad_group_criterion.ad_group='{ag0}' "
            "AND ad_group_criterion.type='KEYWORD'"))
    print(f"keyword criteria live: {kw_total}")
    for g0 in plan["ad_groups"]:
        ag0 = state["adgroups"][g0["name"]]
        for row in query(
                "SELECT ad_group_ad.status, ad_group_ad.ad.type "
                "FROM ad_group_ad "
                f"WHERE ad_group_ad.ad_group='{ag0}'"):
            a = row.get("adGroupAd", {})
            print(f"  ad[{a.get('status')} {a.get('ad', {}).get('type')}] "
                  f"@{g0['name']}")

    print(f"\n=== Search 系列建成并 ENABLE: {name} | ${BUDGET_USD:.0f}/天 | "
          f"{len(plan['ad_groups'])} 组 ===")


if __name__ == "__main__":
    main()
