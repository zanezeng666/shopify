# -*- coding: utf-8 -*-
"""一次性清理：删除半建的试跑 campaign + 探针残留 budget。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
H = {"Content-Type": "application/json", "developer-token": "unused"}
TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


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
    print(f"== {resource} HTTP{r.status_code}: {r.text[:200]}")
    return r.json()


# 1) 删半建 campaign 及其独占 budget
for row in q(
        "SELECT campaign.resource_name, campaign.name, "
        "campaign_budget.resource_name, campaign_budget.name "
        "FROM campaign "
        "WHERE campaign.name = 'Estry Cordless Phone Search'"):
    rn = row["campaign"]["resourceName"]
    print("remove campaign:", rn, row["campaign"]["name"])
    mutate("campaigns", [{"remove": rn}])
    brn = (row.get("campaignBudget") or {}).get("resourceName")
    if brn:
        print("remove budget:", brn,
              row["campaignBudget"].get("name"))
        mutate("campaignBudgets", [{"remove": brn}])

# 2) 删探针残留 budget
for row in q("SELECT campaign_budget.resource_name, campaign_budget.name "
             "FROM campaign_budget "
             "WHERE campaign_budget.name = 'Estry Probe SRCH Budget'"):
    rn = row["campaignBudget"]["resourceName"]
    print("remove budget:", rn)
    mutate("campaignBudgets", [{"remove": rn}])

# 3) 清试跑断点文件
open("/tmp/allcat_ads_done.txt", "w").close()
print("done-file cleared")
