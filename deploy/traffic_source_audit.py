"""Traffic-source audit: where did recent sessions come from, paid vs organic, China vs US, and behavior fingerprints.

A) 11-08~11-16 daily sessions by channel group (pivot)
B) 11-08~11-16 daily sessions by top countries (pivot)  <- did the 11-16 fix kill dirty traffic?
C) 11-01~11-16 top source/medium with engagement
D) geo split of CPC sessions (was ad money buying China/Asia?)
E) behavior fingerprint: US vs China sessions (engagement/duration/depth)
F) 11-16 (post-fix) alone: countries + channels
"""
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
        "limit": 100,
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


def num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except ValueError:
        return v


def pivot(rows, rowkey, colkey, metric_idx=0):
    cols, grid = [], {}
    for r in rows:
        rk = r["dimensionValues"][rowkey]["value"][4:] if rowkey == 0 and r["dimensionValues"][0]["value"].isdigit() else r["dimensionValues"][rowkey]["value"]
        ck = r["dimensionValues"][colkey]["value"]
        cols.append(ck)
        grid.setdefault(rk, {})[ck] = num(r["metricValues"][metric_idx]["value"])
    cols = sorted(set(cols), key=lambda c: -sum(g.get(c, 0) for g in grid.values()))
    return cols, grid


def print_pivot(title, cols, grid, top=8):
    print(f"\n== {title} ==")
    cols = cols[:top]
    head = f"{'':<12}" + "".join(f"{c[:12]:>13}" for c in cols) + f"{'TOTAL':>13}"
    print(head)
    for rk in sorted(grid):
        row = grid[rk]
        print(f"{rk:<12}" + "".join(f"{row.get(c, ''):>13}" if row.get(c, '') != '' else f"{'·':>13}" for c in cols) + f"{sum(row.values()):>13}")


# A) daily sessions by channel
rows = run(["date", "sessionDefaultChannelGroup"], ["sessions"], "2026-11-08", "2026-11-16")
cols, grid = pivot(rows, 0, 1)
print_pivot("A) daily sessions by channel (11-08~11-16)", cols, grid)

# B) daily sessions by country (top8)
rows = run(["date", "country"], ["sessions"], "2026-11-08", "2026-11-16")
cols, grid = pivot(rows, 0, 1)
print_pivot("B) daily sessions by country (11-08~11-16)", cols, grid)

# C) top source/medium full window
rows = run(["sessionSourceMedium"], ["sessions", "totalUsers", "engagedSessions"], "2026-11-01", "2026-11-16")
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
print("\n== C) top source/medium 11-01~16 (sessions / users / engaged) ==")
for r in rows[:14]:
    m = r["metricValues"]
    print(f"  {r['dimensionValues'][0]['value']:<34} sess={m[0]['value']:>6} users={m[1]['value']:>6} engaged={m[2]['value']:>6}")

# D) geo split of CPC sessions
rows = run(["country"], ["sessions"], "2026-11-01", "2026-11-16",
            flt={"filter": {"fieldName": "sessionMedium", "stringFilter": {"matchType": "CONTAINS", "value": "cpc"}}})
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
tot = sum(int(r["metricValues"][0]["value"]) for r in rows)
print(f"\n== D) CPC sessions by country 11-01~16 (total {tot}) ==")
for r in rows[:10]:
    n = int(r["metricValues"][0]["value"])
    print(f"  {r['dimensionValues'][0]['value']:<24} {n:>6}  ({n / tot * 100:.0f}%)")

# E) US vs China behavior fingerprint
rows = run(["country"], ["sessions", "engagedSessions", "averageSessionDuration", "screenPageViews"], "2026-11-01", "2026-11-16",
            flt={"filter": {"fieldName": "country", "inListFilter": {"values": ["United States", "China"]}}})
print("\n== E) US vs China fingerprint (11-01~16) ==")
print(f"  {'country':<16}{'sess':>7}{'engaged':>8}{'eng%':>7}{'avgDur':>8}{'views':>8}")
for r in rows:
    m = [num(x["value"]) for x in r["metricValues"]]
    eng = (m[2] / m[0] * 100) if m[0] else 0
    print(f"  {r['dimensionValues'][0]['value']:<16}{m[0]:>7}{m[2]:>8}{eng:>6.0f}%{m[3]:>8.0f}{m[4]:>8}")

# F) 11-16 post-fix snapshot
rows = run(["country"], ["sessions", "engagedSessions"], "2026-11-16", "2026-11-16")
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
print("\n== F) 11-16 (post-fix day) sessions by country ==")
for r in rows[:10]:
    m = r["metricValues"]
    print(f"  {r['dimensionValues'][0]['value']:<24} sess={m[0]['value']:>5} engaged={m[1]['value']:>5}")
rows = run(["sessionDefaultChannelGroup"], ["sessions"], "2026-11-16", "2026-11-16")
rows.sort(key=lambda r: -int(r["metricValues"][0]["value"]))
print("  -- 11-16 by channel --")
for r in rows:
    print(f"  {r['dimensionValues'][0]['value']:<24} sess={r['metricValues'][0]['value']:>5}")
