# -*- coding: utf-8 -*-
"""GPS RSA 定时重试（退出码0=成功）：Google 爬虫缓存解除后即建成。"""
import json
import sys
import time

import httpx
from ads_create_allcat_search import H, TOK, q  # noqa

CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"


def try_once():
    plan = {p["campaign"]: p for p in
            json.load(open("/tmp/allcat_plans.json"))}[
        "Estry GPS Navigator Search"]
    camp = q("SELECT campaign.resource_name FROM campaign "
             "WHERE campaign.name = 'Estry GPS Navigator Search' "
             "AND campaign.status != 'REMOVED'")
    if not camp:
        print("campaign 缺失")
        return False
    camp = camp[0]["campaign"]["resourceName"]
    rows = q("SELECT ad_group.resource_name FROM ad_group "
             f"WHERE ad_group.campaign = '{camp}' "
             "AND ad_group.status != 'REMOVED'")
    for row in rows:
        ag = row["adGroup"]["resourceName"]
        r = httpx.post(f"{API}/adGroupAds:mutate",
                       headers={**H, "Authorization": f"Bearer {TOK}"},
                       json={"operations": [{
                           "create": {
                               "ad_group": ag, "status": "ENABLED",
                               "ad": {
                                   "responsive_search_ad": {
                                       "headlines": [
                                           {"text": h}
                                           for h in plan["headlines"]],
                                       "descriptions": [
                                           {"text": d}
                                           for d in plan["descriptions"]],
                                       "path1": plan["path1"]},
                                   "final_urls": [plan["url"]]}}}]},
                       timeout=120)
        print(time.strftime("%F %T"), ag, "HTTP", r.status_code, flush=True)
        if r.status_code >= 400:
            print(r.text[:500], flush=True)
            return False
    with open("/tmp/allcat_ads_done.txt", "a") as f:
        f.write("Estry GPS Navigator Search\n")
    print(time.strftime("%F %T"), "ALL RSA OK", flush=True)
    return True


if __name__ == "__main__":
    sys.exit(0 if try_once() else 1)
