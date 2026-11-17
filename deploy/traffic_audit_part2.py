"""Part2: Direct-traffic geo split, 11-16 US session quality, US vs China fingerprint."""
import json
import urllib.request
import urllib.parse

ENV = {}
with open("/home/jason/shopify-admin/.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            ENV[k.strip()] = v.strip()

tok = json.load(urllib.request.urlopen(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({
        "client_id": ENV["GOOGLE_CLIENT_ID"], "client_secret": ENV["GOOGLE_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token",
    }).encode(),
))["access_token"]


def run(dims, mets, d1, d2, flt=None):
    body = {
        "dateRanges": [{"startDate": d1, "endDate": d2}],
        "dimensions": [{"name": d} for d in dims],
        "metrics": [{"name": m} for m in mets],
        "limit": 60,
    }
    if flt:
        body["dimensionFilter"] = flt
    req = urllib.request.Request(
        "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    try:
        return json.load(urllib.request.urlopen(req)).get("rows", [])
    except urllib.error.HTTPError as e:
        print(f"!! GA4 {e.code}: {e.read().decode()[:300]}")
        return []


DIRECT = {"filter": {"fieldName": "sessionSourceMedium", "stringFilter": {"matchType": "EXACT", "value": "(direct) / (none)"}}}

# 1) Direct traffic geo split, full window
rows = run(["country"], ["sessions", "engagedSessions"], "2026-11-01", "2026-11-16", DIRECT)
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
tot = sum(int(r["metricValues"][0]["value"]) for r in rows)
print(f"== 1) DIRECT sessions by country 11-01~16 (total {tot}) ==")
for r in rows[:8]:
    n, e = int(r["metricValues"][0]["value"]), int(r["metricValues"][1]["value"])
    print(f"  {r['dimensionValues'][0]['value']:<24} sess={n:>6} ({n / tot * 100:>3.0f}%)  engaged={e:>5} ({(e / n * 100 if n else 0):>3.0f}%)")

# 2) US vs China fingerprint, split metrics
for mets, label in [(["sessions", "engagedSessions", "averageSessionDuration"], "sess/engaged/avgDur"),
                    (["sessions", "screenPageViews"], "sess/pageviews")]:
    rows = run(["country"], mets, "2026-11-01", "2026-11-16",
               flt={"filter": {"fieldName": "country", "inListFilter": {"values": ["United States", "China", "Singapore", "Brazil"]}}})
    print(f"\n== 2) fingerprint {label} (11-01~16) ==")
    for r in rows:
        vals = [x["value"] for x in r["metricValues"]]
        print(f"  {r['dimensionValues'][0]['value']:<16} " + "  ".join(f"{v:>10}" for v in vals))

# 3) 11-16 US-only: source split + engagement (post-fix day quality)
rows = run(["sessionSourceMedium"], ["sessions", "engagedSessions"], "2026-11-16", "2026-11-16",
           flt={"filter": {"fieldName": "country", "stringFilter": {"matchType": "EXACT", "value": "United States"}}})
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
print("\n== 3) 11-16 US sessions by source (post-fix day) ==")
for r in rows[:8]:
    n, e = int(r["metricValues"][0]["value"]), int(r["metricValues"][1]["value"])
    print(f"  {r['dimensionValues'][0]['value']:<30} sess={n:>5}  engaged={e:>4} ({(e / n * 100 if n else 0):.0f}%)")

# 4) view_item by country for US vs rest on 11-16 (intent quality)
rows = run(["country"], ["eventCount"], "2026-11-16", "2026-11-16",
           flt={"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "EXACT", "value": "view_item"}}})
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
print("\n== 4) 11-16 view_item events by country ==")
for r in rows[:8]:
    print(f"  {r['dimensionValues'][0]['value']:<24} {r['metricValues'][0]['value']:>7}")
