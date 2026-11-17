# -*- coding: utf-8 -*-
"""Serving status summary + hourly spend curve 11-15~17 (was it a sudden stop or gradual?)."""
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


# 1) serving status: only anomalies + counts
stat = defaultdict(list)
for e in q(
        "SELECT campaign.name, campaign.status, campaign.serving_status "
        "FROM campaign WHERE campaign.status != 'REMOVED'"):
    c = e["campaign"]
    stat[(c["status"], c["servingStatus"])].append(c["name"])
print("== campaign (status, serving) -> count ==")
for (st, sv), names in sorted(stat.items(), key=lambda x: -len(x[1])):
    print(f"  {st:>7} / {sv:<14} {len(names)} 个")
    if sv not in ("SERVING",) and len(names) <= 6:
        for n in names:
            print(f"      - {n}")

# 2) hourly spend 11-15 ~ 11-17
hourly = defaultdict(float)
for e in q(
        "SELECT segments.date, segments.hour, metrics.cost_micros "
        "FROM campaign WHERE segments.date BETWEEN '2026-11-15' AND '2026-11-17'"):
    d, h = e["segments"]["date"], int(e["segments"]["hour"])
    hourly[(d, h)] += int(e.get("metrics", {}).get("costMicros", 0)) / 1e6
print("\n== hourly spend ($) 11-15 ~ 11-17 (account tz) ==")
for d in ("2026-11-15", "2026-11-16", "2026-11-17"):
    row = [hourly.get((d, h), 0) for h in range(24)]
    print(f"  {d}: " + " ".join(f"{v:>5.1f}" if v else "   ·" for v in row) + f"  | Σ${sum(row):.0f}")
