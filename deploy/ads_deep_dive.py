# -*- coding: utf-8 -*-
"""Dig: 1) aggregate change_event by type/day 2) non-keyword changes detail
3) current keyword match_types 4) campaign geo criteria raw structure 5) PRESENCE status."""
import json
import os
from collections import Counter, defaultdict

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
        print(f"!! HTTP {r.status_code}: {r.text[:200]}")
        return []
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for batch in rows:
        out.extend(batch.get("results", []))
    return out


# 1) aggregate all changes
rows = q(
    "SELECT change_event.change_date_time, change_event.user_email, change_event.client_type, "
    "change_event.change_resource_type, change_event.changed_fields "
    "FROM change_event "
    "WHERE change_event.change_date_time BETWEEN '2026-11-13 00:00:00' AND '2026-11-17 23:59:59' "
    "LIMIT 10000")
agg = Counter()
detail = []
for e in rows:
    ce = e["changeEvent"]
    day = ce["changeDateTime"][:10]
    rtype = ce.get("changeResourceType", "?")
    agg[(day, rtype)] += 1
    if rtype not in ("AD_GROUP_CRITERION",):
        detail.append((ce["changeDateTime"][:19], rtype,
                       ce.get("changedFields", "")[:80]))
print("== changes by (day, resource_type) ==")
for (day, rtype), n in sorted(agg.items()):
    print(f"  {day}  {rtype:<22} {n}")
print("\n== non-keyword change details ==")
for t, rt, f in sorted(set(detail)):
    print(f"  {t}  {rt:<20} {f}")
kw_changes = sum(n for (d, rt), n in agg.items() if rt == "AD_GROUP_CRITERION")
print(f"\nkeyword-level (AD_GROUP_CRITERION) changes total: {kw_changes}")
kw_days = Counter({d: n for (d, rt), n in agg.items() if rt == "AD_GROUP_CRITERION"})
for d, n in sorted(kw_days.items()):
    print(f"  {d}: {n}")

# 2) current keyword match types
rows = q("SELECT ad_group_criterion.keyword.match_type, campaign.name "
         "FROM ad_group_criterion WHERE campaign.status = 'ENABLED' "
         "AND ad_group_criterion.status = 'ENABLED' AND ad_group_criterion.type = 'KEYWORD' LIMIT 3000")
mt = Counter()
for e in rows:
    mt[e["adGroupCriterion"]["keyword"].get("matchType", "?")] += 1
print("\n== current keyword match types (enabled) ==")
print("  " + ", ".join(f"{k}={v}" for k, v in mt.most_common()))

# 3) geo criteria raw structure (one row)
rows = q("SELECT campaign.name, campaign_criterion.negative, campaign_criterion.geo_target_constant "
         "FROM campaign_criterion WHERE campaign_criterion.type = 'LOCATION' "
         "AND campaign.status = 'ENABLED' LIMIT 3")
print("\n== geo criterion raw row ==")
if rows:
    print(json.dumps(rows[0], ensure_ascii=False)[:400])

# 4) PRESENCE + geo_type status
rows = q("SELECT campaign.name, campaign.positive_geo_target_type, campaign.negative_geo_target_type "
         "FROM campaign WHERE campaign.status = 'ENABLED' LIMIT 50")
gt = Counter()
for e in rows:
    gt[(e["campaign"].get("positiveGeoTargetType", "?"), e["campaign"].get("negativeGeoTargetType", "?"))] += 1
print("\n== (positive, negative) geo target types ==")
for k, v in gt.items():
    print(f"  {k}: {v} campaigns")
