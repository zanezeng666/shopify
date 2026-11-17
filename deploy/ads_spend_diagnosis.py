# -*- coding: utf-8 -*-
"""Why near-zero spend recently? Daily spend trend (11-01~17) + campaign status + serving + budgets."""
import os
from collections import defaultdict

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}

CIDS = ("7059800494", "2214926660", "1651348739")
API = "https://googleads.googleapis.com/v26/customers/{cid}/googleAds:searchStream"


def q(cid, query):
    r = httpx.post(API.format(cid=cid), headers=H, json={"query": query}, timeout=60)
    if r.status_code != 200:
        print(f"!! {cid} HTTP {r.status_code}: {r.text[:200]}")
        return []
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for batch in rows:
        out.extend(batch.get("results", []))
    return out


for cid in CIDS:
    # 1) daily spend across all campaigns
    daily = defaultdict(lambda: [0.0, 0, 0])  # date -> [cost$, clicks, imps]
    res = q(cid, (
        "SELECT segments.date, metrics.cost_micros, metrics.clicks, metrics.impressions "
        "FROM campaign WHERE segments.date BETWEEN '2026-11-01' AND '2026-11-17'"))
    for e in res:
        d, m = e["segments"]["date"], e.get("metrics", {})
        row = daily[d]
        row[0] += int(m.get("costMicros", 0)) / 1e6
        row[1] += int(m.get("clicks", 0))
        row[2] += int(m.get("impressions", 0))
    print(f"\n===== 账号 {cid} 逐日花费 =====")
    for d in sorted(daily):
        c, k, i = daily[d]
        print(f"  {d}  ${c:>7.2f}  clicks={k:>4}  imps={i:>8,}")
    if not daily:
        print("  (11 月无任何投放数据)")

    # 2) campaign status + serving
    res = q(cid, (
        "SELECT campaign.id, campaign.name, campaign.status, campaign.serving_status, "
        "campaign.advertising_channel_type, campaign.budget "
        "FROM campaign WHERE campaign.status != 'REMOVED'"))
    budgets = {e["campaignBudget"]["resourceName"]: e for e in q(cid, (
        "SELECT campaign_budget.resource_name, campaign_budget.amount_micros "
        "FROM campaign_budget"))} if False else {}
    bq = q(cid, ("SELECT campaign_budget.resource_name, campaign_budget.amount_micros "
                 "FROM campaign_budget"))
    bmap = {e["campaignBudget"]["resourceName"]: int(e["campaignBudget"].get("amountMicros", 0)) / 1e6
            for e in bq}
    print(f" -- campaign 现状 --")
    for e in res:
        c = e["campaign"]
        bud = bmap.get(c.get("budget"), 0)
        print(f"  [{c['status']:>7}/{c.get('servingStatus','?'):>9}] "
              f"{c['name'][:38]:<38} {c['advertisingChannelType']:<9} 预算${bud:.2f}/日")
