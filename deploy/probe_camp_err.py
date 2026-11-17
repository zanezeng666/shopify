# -*- coding: utf-8 -*-
"""一次性探针：复现 campaign create payload，dump 完整错误定位 REQUIRED 字段。"""
import json
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


def mutate(resource, ops):
    r = httpx.post(f"{API}/{resource}:mutate",
                   headers={**H, "Authorization": f"Bearer {TOK}"},
                   json={"operations": ops}, timeout=120)
    print(f"== {resource} HTTP{r.status_code}")
    if r.status_code not in (200, 207):
        print(json.dumps(r.json(), indent=1, ensure_ascii=False)[:3000])
        raise SystemExit(1)
    return r.json()


budget = mutate("campaignBudgets", [{
    "create": {"name": "Estry Probe SRCH Budget",
               "amount_micros": "50000000",
               "explicitly_shared": False,
               "delivery_method": "STANDARD"}}])["results"][0]["resourceName"]
strat = "customers/7059800494/biddingStrategies/12310786752"
print("budget:", budget)
try:
    r = mutate("campaigns", [{
        "create": {
            "name": "Estry Probe Search TMP", "status": "PAUSED",
            "advertising_channel_type": "SEARCH",
            "campaign_budget": budget,
            "bidding_strategy": strat,
            "network_settings": {
                "target_google_search": True,
                "target_search_network": False,
                "target_content_network": False,
                "target_partner_search_network": False},
        }}])
    print("campaign created:", r["results"][0]["resourceName"])
except SystemExit:
    pass
