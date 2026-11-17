# -*- coding: utf-8 -*-
"""失败 5 项修复：
A) GPS Navigator: campaign/组/词已建好，只差 RSA——直接重试（落地页
   429 属 Shopify 边缘对数据中心 IP 偶发 challenge，Google 爬虫可正常访问）
B) Barcode Scanner / Power Tool / PLC / RAID Controller:
   关键词净化 -> 删半建 campaign+budget -> 复用 build_one 重建
"""
import copy
import json
import re
import time

import httpx
from ads_create_allcat_search import build_one, ensure_shared, q  # noqa
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
H = {"Content-Type": "application/json", "developer-token": "unused"}
import os  # noqa: E402

TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]

KW_FIX = ["Estry Barcode Scanner Search", "Estry Power Tool Search",
          "Estry PLC Search", "Estry RAID Controller Search"]
GPS = "Estry GPS Navigator Search"
DONE = "/tmp/allcat_ads_done.txt"


def mutate(resource, ops):
    r = httpx.post(f"{API}/{resource}:mutate",
                   headers={**H, "Authorization": f"Bearer {TOK}"},
                   json={"operations": ops}, timeout=120)
    if r.status_code not in (200, 207):
        raise RuntimeError(f"HTTP{r.status_code} {resource}: {r.text[:300]}")
    return r.json()


def sanitize_kw(text):
    """Google 关键词合法字符=字母数字空格连字符&.，其他全删；词数<=10。"""
    t = re.sub(r"[^A-Za-z0-9 &.\-]", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    if not (1 <= len(t.split()) <= 10) or len(t) < 2:
        return None
    return t


def drop_campaign(name):
    rows = q("SELECT campaign.resource_name, campaign.name, "
             "campaign_budget.resource_name, campaign_budget.name "
             "FROM campaign WHERE campaign.name "
             f"= '{name}' AND campaign.status != 'REMOVED'")
    for row in rows:
        rn = row["campaign"]["resourceName"]
        print("  remove campaign:", rn)
        mutate("campaigns", [{"remove": rn}])
        brn = (row.get("campaignBudget") or {}).get("resourceName")
        if brn:
            print("  remove budget:", brn)
            mutate("campaignBudgets", [{"remove": brn}])


def fix_gps():
    plan = next(p for p in PLANS if p["campaign"] == GPS)
    camp = q("SELECT campaign.resource_name FROM campaign "
             f"WHERE campaign.name = '{GPS}' "
             "AND campaign.status != 'REMOVED'")
    if not camp:
        print("GPS campaign 缺失")
        return False
    camp = camp[0]["campaign"]["resourceName"]
    rows = q("SELECT ad_group.resource_name FROM ad_group "
             f"WHERE ad_group.campaign = '{camp}' "
             "AND ad_group.status != 'REMOVED'")
    for attempt in range(3):
        try:
            for row in rows:
                ag = row["adGroup"]["resourceName"]
                mutate("adGroupAds", [{
                    "create": {"ad_group": ag, "status": "ENABLED", "ad": {
                        "responsive_search_ad": {
                            "headlines": [{"text": h}
                                          for h in plan["headlines"]],
                            "descriptions": [{"text": d}
                                             for d in plan["descriptions"]],
                            "path1": plan["path1"]},
                        "final_urls": [plan["url"]]}}}])
                print("  RSA ok:", ag)
            with open(DONE, "a") as f:
                f.write(GPS + "\n")
            return True
        except RuntimeError as e:
            print(f"  RSA 重试{attempt + 1}失败: {str(e)[:200]}")
            time.sleep(8)
    return False


def fix_kw(name, strat, neg_id, callout_rns):
    plan = copy.deepcopy(next(p for p in PLANS if p["campaign"] == name))
    dropped = kept = 0
    clean_groups = []
    for g in plan["ad_groups"]:
        kws = []
        for mt, kw in g["keywords"]:
            t = sanitize_kw(kw)
            if t:
                kws.append((mt, t))
                kept += 1
            else:
                dropped += 1
        if kws:
            g["keywords"] = kws
            clean_groups.append(g)
    plan["ad_groups"] = clean_groups
    print(f"  关键词净化: 保留{kept} 丢弃{dropped} 组{len(clean_groups)}")
    drop_campaign(name)
    build_one(plan, strat, neg_id, callout_rns)
    with open(DONE, "a") as f:
        f.write(name + "\n")


def main():
    global PLANS
    PLANS = json.load(open("/tmp/allcat_plans.json"))
    print("== A: GPS RSA 重试")
    gps_ok = fix_gps()
    print("== B: 关键词净化重建 4 项")
    strat, neg_id, callout_rns = ensure_shared()
    for name in KW_FIX:
        print("--", name)
        try:
            fix_kw(name, strat, neg_id, callout_rns)
        except Exception as e:  # noqa: BLE001
            print("  FAIL:", str(e)[:260])
        time.sleep(1)
    print(f"== 完成 GPS={'OK' if gps_ok else 'FAIL'} ==")


if __name__ == "__main__":
    main()
