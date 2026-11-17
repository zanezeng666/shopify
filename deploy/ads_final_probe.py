# -*- coding: utf-8 -*-
"""Final probe: a) target of status/budget changes b) budget sharing c) geo list d) PRESENCE."""
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
        print(f"!! HTTP {r.status_code}: {r.text[:180]}")
        return []
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for batch in rows:
        out.extend(batch.get("results", []))
    return out


# a) details of the status flips + budget change (old/new resource)
print("== a) status & budget change targets ==")
for e in q(
        "SELECT change_event.change_date_time, change_event.change_resource_type, "
        "change_event.changed_fields, change_event.old_resource, change_event.new_resource "
        "FROM change_event "
        "WHERE change_event.change_date_time BETWEEN '2026-11-15 21:00:00' AND '2026-11-16 12:15:00' "
        "AND change_event.change_resource_type IN ('CAMPAIGN', 'CAMPAIGN_BUDGET') LIMIT 200"):
    ce = e["changeEvent"]
    if "status" in ce.get("changedFields", "") or "amountMicros" in ce.get("changedFields", ""):
        print(f"  {ce['changeDateTime'][:19]} {ce['changeResourceType']:<16} "
              f"{ce.get('changedFields','')[:40]:<40} {ce.get('newResource', ce.get('oldResource',''))}")

# b) budgets with sharing
print("\n== b) all budgets ==")
for e in q("SELECT campaign_budget.name, campaign_budget.amount_micros, campaign_budget.status, "
           "campaign_budget.explicitly_shared, campaign_budget.total_amount_micros "
           "FROM campaign_budget LIMIT 60"):
    b = e["campaignBudget"]
    total = f" total=¥{int(b.get('totalAmountMicros', 0)) / 1e6:.0f}" if b.get("totalAmountMicros") else ""
    print(f"  [{b['status']:<7}] {'SHARED' if b.get('explicitlyShared') else 'own   '} "
          f"¥{int(b.get('amountMicros', 0)) / 1e6:>7.2f}/日 {b['name'][:40]}{total}")

# campaigns per shared budget
cmap = defaultdict(list)
for e in q("SELECT campaign.name, campaign.budget FROM campaign "
           "WHERE campaign.status = 'ENABLED' LIMIT 60"):
    cmap[e["campaign"]["budget"]].append(e["campaign"]["name"])
shared = {b: cs for b, cs in cmap.items() if len(cs) > 1}
print(f"\n  shared budgets: {len(shared)}")
for b, cs in shared.items():
    print(f"    {b.split('/')[-1]}: {len(cs)} campaigns e.g. {cs[0][:30]}")

# c) geo list (fixed parsing)
print("\n== c) campaign geo criteria ==")
geo_by_camp = defaultdict(list)
for e in q("SELECT campaign.name, campaign_criterion.negative, "
           "campaign_criterion.location.geo_target_constant, campaign_criterion.type "
           "FROM campaign_criterion WHERE campaign_criterion.type = 'LOCATION' "
           "AND campaign.status = 'ENABLED' LIMIT 500"):
    cc = e["campaignCriterion"]
    ref = (cc.get("location") or {}).get("geoTargetConstant", "")
    gid = ref.split("/")[-1] if ref else "?"
    geo_by_camp[e["campaign"]["name"]].append(("-" if cc.get("negative") else "+") + gid)
ids = sorted({g.lstrip("+-") for v in geo_by_camp.values() for g in v if g != "?"})
names = {}
if ids:
    idl = ",".join(f'"{i}"' for i in ids[:40])
    for e in q(f"SELECT geo_target_constant.id, geo_target_constant.name, geo_target_constant.country_code "
               f"FROM geo_target_constant WHERE geo_target_constant.id IN ({idl}) LIMIT 50"):
        g = e["geoTargetConstant"]
        names[str(g["id"])] = f"{g['name']}({g.get('countryCode', '')})"
for cname, gs in sorted(geo_by_camp.items()):
    pretty = Counter(names.get(g.lstrip("+-"), "?" + g) for g in gs)
    print(f"  {cname[:34]:<34} " + ", ".join(f"{k}x{v}" if v > 1 else k for k, v in pretty.items()))

# d) PRESENCE status now
print("\n== d) PRESENCE status ==")
gt = Counter()
for e in q("SELECT campaign.name, campaign.positive_geo_target_type, campaign.negative_geo_target_type "
           "FROM campaign WHERE campaign.status = 'ENABLED' LIMIT 60"):
    c = e["campaign"]
    gt[(c.get("positiveGeoTargetType", "?"), c.get("negativeGeoTargetType", "?"))] += 1
for k, v in gt.items():
    print(f"  positive={k[0]}, negative={k[1]}: {v} campaigns")
