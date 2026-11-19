"""GA4 chatgpt 来源按日趋势（无 orderBys 变体）"""
import os, httpx

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport"
CHAT = {"filter": {"fieldName": "sessionSource",
                   "stringFilter": {"value": "chatgpt", "matchType": "CONTAINS"}}}

j = httpx.post(URL, headers=H, json={
    "dateRanges": [{"startDate": "2026-10-05", "endDate": "2026-11-19"}],
    "dimensions": [{"name": "date"}],
    "metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
    "dimensionFilter": CHAT}, timeout=60).json()
rows = j.get("rows") or []
print(f"[date 无 orderBys] rows={len(rows)} rowCount={j.get('rowCount')}")
for r in rows:
    print("  " + " | ".join([d["value"] for d in r["dimensionValues"]] +
                            [m["value"] for m in r["metricValues"]]))
