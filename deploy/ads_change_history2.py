# -*- coding: utf-8 -*-
"""Change history + geo targeting, with error detail and field fallbacks."""
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


def q(query, tag=""):
    r = httpx.post(API, headers=H, json={"query": query}, timeout=60)
    if r.status_code != 200:
        txt = r.text
        import re
        m = re.search(r'"message":\s*"([^"]+)"', txt)
        errs = re.findall(r'"(INVALID_ARGUMENT|[A-Z_]+)"\s*,?\s*\n?\s*"?[a-zA-Z_]*"?', txt[:2000])
        print(f"!! {tag} HTTP {r.status_code}: {m.group(1) if m else txt[:200]}")
        return []
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for batch in rows:
        out.extend(batch.get("results", []))
    return out


# 1) change history (no ORDER BY)
print("== change_event 11-14 ~ 11-17 ==")
rows = q(
    "SELECT change_event.change_date_time, change_event.user_email, change_event.client_type, "
    "change_event.change_resource_type, change_event.changed_fields "
    "FROM change_event "
    "WHERE change_event.change_date_time BETWEEN '2026-11-14 00:00:00' AND '2026-11-17 23:59:59'", "ch")
for e in rows:
    ce = e["changeEvent"]
    fields = ",".join(ce.get("changedFields", []))[:70]
    print(f"  {ce['changeDateTime'][:19]}  {ce.get('clientType',''):<11} {ce.get('userEmail','')[:20]:<20} "
          f"{ce.get('changeResourceType',''):<15} {fields}")

# 2) geo criteria - try legacy field path
print("\n== campaign LOCATION criteria ==")
geo_by_camp = defaultdict(list)
rows = q(
    "SELECT campaign.name, campaign_criterion.negative, campaign_criterion.geo_target_constant, "
    "campaign_criterion.type_ FROM campaign_criterion "
    "WHERE campaign_criterion.type_ = 'LOCATION' AND campaign.status = 'ENABLED'", "geo")
for e in rows:
    cname = e["campaign"]["name"]
    neg = e["campaignCriterion"].get("negative", False)
    gref = e["campaignCriterion"].get("geoTargetConstant", "")
    gid = gref.split("/")[-1] if gref else "?"
    geo_by_camp[cname].append(("-" if neg else "+") + gid)

ids = sorted({g.lstrip("+-") for v in geo_by_camp.values() for g in v if g != "?"})
names = {}
if ids:
    idl = ",".join(f'"{i}"' for i in ids[:40])
    for e in q(f"SELECT geo_target_constant.id, geo_target_constant.name, geo_target_constant.country_code "
               f"FROM geo_target_constant WHERE geo_target_constant.id IN ({idl})", "names"):
        g = e["geoTargetConstant"]
        names[str(g["id"])] = f"{g['name']}({g.get('countryCode','')})"

for cname, gs in sorted(geo_by_camp.items()):
    pretty = Counter(names.get(g.lstrip("+-"), g) for g in gs)
    print(f"  {cname[:36]:<36} " + ", ".join(f"{k}x{v}" if v > 1 else k for k, v in pretty.items()))

# 3) all criterion types summary (language? user interest?)
print("\n== criterion type summary (enabled campaigns) ==")
for e in q("SELECT campaign_criterion.type_, campaign_criterion.negative "
           "FROM campaign_criterion WHERE campaign.status = 'ENABLED'", "types"):
    pass
types = Counter()
for e in q("SELECT campaign_criterion.type_ FROM campaign_criterion "
           "WHERE campaign.status = 'ENABLED'", "types"):
    types[e["campaignCriterion"]["type_"]] += 1
print("  " + ", ".join(f"{k}={v}" for k, v in types.most_common()))
