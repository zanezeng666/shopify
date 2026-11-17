# -*- coding: utf-8 -*-
"""各分类搜索广告批量创建。

复刻 ads_create_med_search.py 已验证模式，批量建 38 个分类 campaign：
  预算各 ¥50/天(账户CNY) + 组合MaxClicks(共享cap1.5) + US定位/英语
  + 复用/新建共享负词组与callout + 每 campaign: generic组+3品牌组+RSA
全部 ENABLED 直接投放；断点 /tmp/allcat_ads_done.txt；限速0.3s/mutate。
"""
import json
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
H = {"Content-Type": "application/json", "developer-token": "unused"}
NEG_WORDS = ["battery tester", "rebuild", "repacking", "repack", "repair",
             "diy", "how to", "wholesale", "distributor", "bulk", "connector",
             "charger only", "dock", "battery charger"]
CALLOUTS = ["US Stock", "Fast US Shipping", "1-Year Warranty",
            "Check Model Fit"]
DONE = "/tmp/allcat_ads_done.txt"
LOG = "/home/jason/shopify-admin/deploy/allcat_ads.log"


def log(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


def q(gaql):
    r = httpx.post(f"{API}/googleAds:search",
                   headers={**H, "Authorization": f"Bearer {TOK}"},
                   json={"query": gaql}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GAQL HTTP{r.status_code}: {r.text[:400]}")
    d = r.json()
    return d.get("results") or d.get("rows") or []


def mutate(resource, ops, partial=False):
    body = {"operations": ops}
    last = None
    for attempt in range(3):
        try:
            r = httpx.post(f"{API}/{resource}:mutate",
                           headers={**H, "Authorization": f"Bearer {TOK}"},
                           json=body, timeout=120)
            if r.status_code in (200, 207):
                return r.json()
            try:
                errs = r.json()["error"]["details"][0]["errors"]
                detail = "; ".join(
                    f"{e.get('errorCode')}@"
                    f"{(e.get('location') or {}).get('fieldPath', '')}: "
                    f"{e.get('message', '')[:200]}" for e in errs[:3])
            except Exception:  # noqa: BLE001
                detail = r.text[:300]
            last = RuntimeError(f"HTTP{r.status_code} {resource}: {detail}")
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(2 + attempt * 3)
    raise last


def rid(res):
    return res.rsplit("/", 1)[-1]


def ensure_shared():
    # 1) 组合出价策略
    strat = None
    for row in q("SELECT bidding_strategy.resource_name, bidding_strategy.name "
                 "FROM bidding_strategy"):
        if row["biddingStrategy"]["name"] == "MaxClicks Estry Cat cap150":
            strat = row["biddingStrategy"]["resourceName"]
            break
    if not strat:
        r = mutate("biddingStrategies", [{
            "create": {
                "name": "MaxClicks Estry Cat cap150",
                "target_spend": {"cpc_bid_ceiling_micros": "1500000"},
            }}])
        strat = r["results"][0]["resourceName"]
    log(f"出价策略: {strat}")

    # 2) 共享负词组
    neg_id, neg_rn = None, None
    for row in q("SELECT shared_set.id, shared_set.resource_name, "
                 "shared_set.name FROM shared_set "
                 "WHERE shared_set.type='NEGATIVE_KEYWORDS'"):
        if row["sharedSet"]["name"] == "Estry Search Negatives":
            neg_rn = row["sharedSet"]["resourceName"]
            neg_id = row["sharedSet"]["id"]
            break
    if not neg_rn:
        r = mutate("sharedSets", [{
            "create": {"name": "Estry Search Negatives",
                       "type": "NEGATIVE_KEYWORDS"}}])
        neg_rn = r["results"][0]["resourceName"]
        neg_id = rid(neg_rn)
        ops = [{"create": {"shared_set": neg_rn,
                           "keyword": {"text": w, "match_type": "PHRASE"}}}
               for w in NEG_WORDS]
        mutate("sharedCriteria", ops)
    log(f"负词组: {neg_rn} (id={neg_id})")

    # 3) callouts（按文本 dedupe）
    have = {}
    for row in q("SELECT asset.resource_name, asset.callout_asset.callout_text "
                 "FROM asset WHERE asset.type='CALLOUT'"):
        t = (row["asset"].get("calloutAsset") or {}).get("calloutText")
        if t:
            have[t] = row["asset"]["resourceName"]
    callout_rns = []
    for c in CALLOUTS:
        if c in have:
            callout_rns.append(have[c])
            continue
        r = mutate("assets", [{
            "create": {"callout_asset": {"callout_text": c}}}])
        callout_rns.append(r["results"][0]["resourceName"])
    log(f"callouts: {len(callout_rns)} 个")
    return strat, neg_id, callout_rns


def build_one(plan, strat, neg_id, callout_rns):
    name = plan["campaign"]
    core = name.replace("Estry ", "").replace(" Search", "")
    # budget
    r = mutate("campaignBudgets", [{
        "create": {"name": f"Estry {core} SRCH Budget",
                   "amount_micros": "50000000",
                   "explicitly_shared": False,
                   "delivery_method": "STANDARD"}}])
    budget = r["results"][0]["resourceName"]
    # campaign (ENABLED 直接投放)
    r = mutate("campaigns", [{
        "create": {
            "name": name, "status": "ENABLED",
            "advertising_channel_type": "SEARCH",
            "campaign_budget": budget,
            "bidding_strategy": strat,
            "contains_eu_political_advertising":
                "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
            "network_settings": {
                "target_google_search": True,
                "target_search_network": False,
                "target_content_network": False,
                "target_partner_search_network": False},
        }}])
    camp = r["results"][0]["resourceName"]
    # criteria: US geo + English
    mutate("campaignCriteria", [
        {"create": {"campaign": camp, "location": {
            "geo_target_constant": "geoTargetConstants/2840"}}},
        {"create": {"campaign": camp, "language": {
            "language_constant": "languageConstants/1000"}}},
    ])
    # 负词组 + callouts 挂载
    mutate("campaignSharedSets", [{"create": {
        "campaign": camp, "shared_set":
            f"customers/{CID}/sharedSets/{neg_id}"}}])
    mutate("campaignAssets", [{"create": {
        "campaign": camp, "asset": a, "field_type": "CALLOUT"}}
        for a in callout_rns])
    # ad groups
    ag_rns = []
    for g in plan["ad_groups"]:
        r = mutate("adGroups", [{"create": {
            "name": g["name"][:255], "campaign": camp,
            "status": "ENABLED", "type": "SEARCH_STANDARD"}}])
        ag_rns.append((g, r["results"][0]["resourceName"]))
        time.sleep(0.2)
    # keywords
    for g, ag in ag_rns:
        ops = [{"create": {
            "ad_group": ag, "status": "ENABLED",
            "keyword": {"text": kw[:80], "match_type": mt}}}
            for mt, kw in g["keywords"]]
        if ops:
            mutate("adGroupCriteria", ops)
            time.sleep(0.2)
    # RSA：每个 ad group 一条（内联文字，品牌组无广告不投放）
    for g, ag in ag_rns:
        mutate("adGroupAds", [{
            "create": {
                "ad_group": ag, "status": "ENABLED",
                "ad": {
                    "responsive_search_ad": {
                        "headlines": [{"text": h}
                                      for h in plan["headlines"]],
                        "descriptions": [{"text": d}
                                         for d in plan["descriptions"]],
                        "path1": plan["path1"],
                    },
                    "final_urls": [plan["url"]],
                }}}])
        time.sleep(0.2)
    n_kw = sum(len(g["keywords"]) for g, _ in ag_rns)
    log(f"OK {name}: {len(ag_rns)}组/{n_kw}词/"
        f"{len(plan['headlines'])}H/{len(plan['descriptions'])}D/"
        f"{len(ag_rns)}RSA -> {plan['url']}")


def main():
    plans = json.load(open("/tmp/allcat_plans.json"))
    if len(__import__("sys").argv) > 1:  # 试跑: 传数字限制条数
        plans = plans[: int(__import__("sys").argv[1])]
    existing = {row["campaign"]["name"] for row in q(
        "SELECT campaign.name FROM campaign "
        "WHERE campaign.status != 'REMOVED'")}
    try:
        done = {x.strip() for x in open(DONE)}
    except FileNotFoundError:
        done = set()
    strat, neg_id, callout_rns = ensure_shared()
    ok = skip = fail = 0
    for i, plan in enumerate(plans, 1):
        name = plan["campaign"]
        if name in existing or name in done:
            skip += 1
            continue
        try:
            build_one(plan, strat, neg_id, callout_rns)
            ok += 1
            with open(DONE, "a") as f:
                f.write(name + "\n")
        except Exception as e:  # noqa: BLE001
            fail += 1
            log(f"FAIL {name}: {str(e)[:260]}")
        time.sleep(1.0)
    log(f"== 完成: ok={ok} skip={skip} fail={fail} / 共{len(plans)} ==")


if __name__ == "__main__":
    main()
