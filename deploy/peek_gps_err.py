# -*- coding: utf-8 -*-
"""GPS RSA 完整 policy 错误 dump。"""
import json

import httpx
from ads_create_allcat_search import q  # noqa

CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
from ads_create_allcat_search import H, TOK  # noqa

plans = {p["campaign"]: p for p in json.load(open("/tmp/allcat_plans.json"))}
plan = plans["Estry GPS Navigator Search"]
camp = q("SELECT campaign.resource_name FROM campaign "
         "WHERE campaign.name = 'Estry GPS Navigator Search' "
         "AND campaign.status != 'REMOVED'")[0]["campaign"]["resourceName"]
ag = q("SELECT ad_group.resource_name FROM ad_group "
       f"WHERE ad_group.campaign = '{camp}' "
       "AND ad_group.status != 'REMOVED'")[0]["adGroup"]["resourceName"]
r = httpx.post(f"{API}/adGroupAds:mutate",
               headers={**H, "Authorization": f"Bearer {TOK}"},
               json={"operations": [{
                   "create": {"ad_group": ag, "status": "ENABLED", "ad": {
                       "responsive_search_ad": {
                           "headlines": [{"text": h}
                                         for h in plan["headlines"]],
                           "descriptions": [{"text": d}
                                            for d in plan["descriptions"]],
                           "path1": plan["path1"]},
                       "final_urls": [plan["url"]]}}}]}, timeout=120)
print("HTTP", r.status_code)
if r.status_code >= 400:
    print(json.dumps(r.json(), indent=1, ensure_ascii=False)[:3000])
else:
    print("SUCCESS:", r.json())
