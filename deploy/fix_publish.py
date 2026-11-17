# -*- coding: utf-8 -*-
"""发布 3 个未发布 collection -> GPS 重试 RSA -> 查广告政策状态。"""
import json
import time

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
import os  # noqa: E402

CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
H = {"Content-Type": "application/json", "developer-token": "unused"}
TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]

from shopify_admin.services.stores.service import StoreService  # noqa: E402

UNPUB = [
    ("custom_collections.json", "custom_collections",
     "custom_collection", 159759990884, "gps-navigator-battery"),
    ("custom_collections.json", "custom_collections",
     "custom_collection", 514118877428, "equipment-survey-test-battery"),
    ("custom_collections.json", "custom_collections",
     "custom_collection", 159760875620, "pda-pocket-pc-battery"),
]


def q(gaql):
    r = httpx.post(f"{API}/googleAds:search",
                   headers={**H, "Authorization": f"Bearer {TOK}"},
                   json={"query": gaql}, timeout=60)
    r.raise_for_status()
    return (r.json().get("results") or [])


def mutate(resource, ops):
    r = httpx.post(f"{API}/{resource}:mutate",
                   headers={**H, "Authorization": f"Bearer {TOK}"},
                   json={"operations": ops}, timeout=120)
    if r.status_code not in (200, 207):
        raise RuntimeError(f"HTTP{r.status_code} {resource}: {r.text[:400]}")
    return r.json()


def main():
    client = StoreService().get_client(1)
    # 1) 发布 3 个 collection（custom 失败换 smart 端点再试）
    for ep, key, wrap, cid, handle in UNPUB:
        done = False
        for w in (wrap, "smart_collection"):
            try:
                e = ("custom_collections" if w == "custom_collection"
                     else "smart_collections")
                r = client.request("PUT", f"{e}/{cid}.json",
                                   json_body={w: {"id": cid,
                                                  "published": True}})
                print("published", handle, "via", w,
                      (r.get(w) or {}).get("published_at"))
                done = True
                break
            except Exception as ex:  # noqa: BLE001
                print("  try", w, "fail:", str(ex)[:120])
        if not done:
            print("PUBLISH FAIL:", handle)
        time.sleep(0.5)
    client.close()

    # 2) GPS 重试 RSA
    plans = {p["campaign"]: p for p in
             json.load(open("/tmp/allcat_plans.json"))}
    plan = plans["Estry GPS Navigator Search"]
    camp = q("SELECT campaign.resource_name FROM campaign "
             "WHERE campaign.name = 'Estry GPS Navigator Search' "
             "AND campaign.status != 'REMOVED'")
    if camp:
        camp = camp[0]["campaign"]["resourceName"]
        rows = q("SELECT ad_group.resource_name FROM ad_group "
                 f"WHERE ad_group.campaign = '{camp}' "
                 "AND ad_group.status != 'REMOVED'")
        ok = False
        for attempt in range(3):
            try:
                for row in rows:
                    ag = row["adGroup"]["resourceName"]
                    mutate("adGroupAds", [{
                        "create": {"ad_group": ag, "status": "ENABLED",
                                   "ad": {
                                       "responsive_search_ad": {
                                           "headlines": [
                                               {"text": h} for h in
                                               plan["headlines"]],
                                           "descriptions": [
                                               {"text": d} for d in
                                               plan["descriptions"]],
                                           "path1": plan["path1"]},
                                       "final_urls": [plan["url"]]}}}])
                    print("RSA ok:", ag)
                ok = True
                break
            except RuntimeError as e:
                print(f"RSA 重试{attempt + 1}失败: {str(e)[:200]}")
                time.sleep(10)
        if ok:
            with open("/tmp/allcat_ads_done.txt", "a") as f:
                f.write("Estry GPS Navigator Search\n")
    else:
        print("GPS campaign 缺失")

    # 3) 查 Equipment/PDA/GPS 广告政策状态（campaign 名从 plans 实取）
    all_plans = json.load(open("/tmp/allcat_plans.json"))
    names = [p["campaign"] for p in all_plans
             if any(t in p["campaign"].lower()
                    for t in ("equipment", "pda", "gps"))]
    print("待查 campaign:", names)
    for nm in names:
        rows = q("SELECT ad_group_ad.policy_summary.approval_status, "
                 "ad_group_ad.status, campaign.name "
                 "FROM ad_group_ad WHERE campaign.name "
                 f"= '{nm}' AND ad_group_ad.status != 'REMOVED'")
        if not rows:
            print(nm, "| 无广告")
        for r in rows:
            pol = (r.get("adGroupAd", {}).get("policySummary") or {})
            print(nm, "| ad status:", r["adGroupAd"]["status"],
                  "| approval:", pol.get("approvalStatus"),
                  pol.get("policyTopicEntries"))


if __name__ == "__main__":
    main()
