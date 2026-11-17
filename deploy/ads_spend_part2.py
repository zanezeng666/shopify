# -*- coding: utf-8 -*-
"""Campaign-level daily spend (11-14~17) + status/serving + budgets, main CID only."""
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
CID = "7059800494"
API = f"https://googleads.googleapis.com/v26/customers/{CID}/googleAds:searchStream"


def q(query):
    r = httpx.post(API, headers=H, json={"query": query}, timeout=60)
    if r.status_code != 200:
        print(f"!! HTTP {r.status_code}: {r.text[:300]}")
        return []
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for batch in rows:
        out.extend(batch.get("results", []))
    return out


# 1) campaign x date since 11-14 (the collapse window)
grid = defaultdict(dict)
names = {}
for e in q(
        "SELECT campaign.name, segments.date, metrics.cost_micros, metrics.clicks, metrics.impressions "
        "FROM campaign WHERE segments.date BETWEEN '2026-11-14' AND '2026-11-17'"):
    c, d, m = e["campaign"]["name"], e["segments"]["date"], e.get("metrics", {})
    names[c] = 1
    grid[c][d] = (int(m.get("costMicros", 0)) / 1e6, int(m.get("clicks", 0)), int(m.get("impressions", 0)))
print("== campaign x date (11-14 ~ 11-17, cost$/clicks/imps) ==")
dates = ["2026-11-14", "2026-11-15", "2026-11-16", "2026-11-17"]
for c in sorted(grid, key=lambda n: -sum(v[0] for v in grid[n].values())):
    cells = []
    for d in dates:
        v = grid[c].get(d)
        cells.append(f"${v[0]:>7.2f}/{v[1]:>3}ck/{v[2]:>6,}im" if v else f"{'—':>22}")
    print(f"  {c[:34]:<34} " + " | ".join(cells))

# 2) status + serving_status
print("\n== campaign status / serving ==")
for e in q(
        "SELECT campaign.id, campaign.name, campaign.status, campaign.serving_status, "
        "campaign.advertising_channel_type FROM campaign WHERE campaign.status != 'REMOVED'"):
    c = e["campaign"]
    print(f"  [{c['status']:>7}/{c['servingStatus']:>12}] {c['name'][:40]:<40} {c['advertisingChannelType']}")

# 3) budgets
print("\n== budgets ==")
for e in q("SELECT campaign_budget.name, campaign_budget.amount_micros, campaign_budget.status "
           "FROM campaign_budget"):
    b = e["campaignBudget"]
    print(f"  [{b['status']:>7}] {b['name'][:36]:<36} ${int(b.get('amountMicros', 0)) / 1e6:.2f}/日")
