# -*- coding: utf-8 -*-
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
        print(f"!! HTTP {r.status_code}: {r.text[:250]}")
        return None
    rows = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for batch in rows:
        out.extend(batch.get("results", []))
    return out


# 1) change history
print("== change_event 11-14 ~ 11-17 ==")
rows = q(
    "SELECT change_event.change_date_time, change_event.user_email, change_event.client_type, "
    "change_event.change_resource_type, change_event.changed_fields "
    "FROM change_event "
    "WHERE change_event.change_date_time BETWEEN '2026-11-14 00:00:00' AND '2026-11-17 23:59:59' LIMIT 10000")
if rows is not None:
    for e in rows:
        ce = e["changeEvent"]
        fields = ",".join(ce.get("changedFields", []))[:80]
        print(f"  {ce['changeDateTime'][:19]}  {ce.get('clientType',''):<11} "
              f"{ce.get('userEmail','')[:20]:<20} {ce.get('changeResourceType',''):<15} {fields}")

# 2) geo criteria
print("\n== campaign LOCATION criteria ==")
geo_by_camp = defaultdict(list)
for path in ("campaign_criterion.location.geo_target_constant", "campaign_criterion.geo_target_constant"):
    query = (f"SELECT campaign.name, campaign_criterion.negative, {path}, campaign_criterion.type "
             "FROM campaign_criterion WHERE campaign_criterion.type = 'LOCATION' "
             "AND campaign.status = 'ENABLED' LIMIT 500")
    rows = q(query)
    if rows:
        for e in rows:
            cname = e["campaign"]["name"]
            neg = e["campaignCriterion"].get("negative", False)
            ref = e["campaignCriterion"]
            for seg in path.split("."):
                ref = (ref or {}).get(seg) if isinstance(ref, dict) else None
            gid = str(ref).split("/")[-1] if ref else "?"
            geo_by_camp[cname].append(("-" if neg else "+") + gid)
        break
    print(f"  (path {path} failed, trying next)")

ids = sorted({g.lstrip("+-") for v in geo_by_camp.values() for g in v if g != "?"})
names = {}
if ids:
    idl = ",".join(f'"{i}"' for i in ids[:40])
    rows = q(f"SELECT geo_target_constant.id, geo_target_constant.name, geo_target_constant.country_code "
             f"FROM geo_target_constant WHERE geo_target_constant.id IN ({idl}) LIMIT 50")
    for e in rows or []:
        g = e["geoTargetConstant"]
        names[str(g["id"])] = f"{g['name']}({g.get('countryCode','')})"

for cname, gs in sorted(geo_by_camp.items()):
    pretty = Counter(names.get(g.lstrip("+-"), g) for g in gs)
    print(f"  {cname[:36]:<36} " + ", ".join(f"{k}x{v}" if v > 1 else k for k, v in pretty.items()))
