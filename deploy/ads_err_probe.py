# -*- coding: utf-8 -*-
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
CID = "7059800494"
API = f"https://googleads.googleapis.com/v26/customers/{CID}/googleAds:searchStream"

TESTS = {
    "ch_min": "SELECT change_event.change_date_time, change_event.change_resource_type "
              "FROM change_event WHERE change_event.change_date_time DURING YESTERDAY",
    "crit_min": "SELECT campaign_criterion.type_ FROM campaign_criterion "
                "WHERE campaign.status = 'ENABLED' LIMIT 5",
    "crit_by_camp": "SELECT campaign_criterion.type_ FROM campaign_criterion LIMIT 5",
}
for tag, query in TESTS.items():
    r = httpx.post(API, headers=H, json={"query": query}, timeout=60)
    print(f"--- {tag}: HTTP {r.status_code}")
    print(r.text[:1500])
    print()
