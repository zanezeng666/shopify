"""GA4 payment-funnel verification: did anyone actually reach payment selection?

Reports (2026-11-01 ~ 2026-11-16):
  1. funnel events by activeUsers: add_to_cart / begin_checkout / add_shipping_info / add_payment_info / purchase
  2. begin_checkout by country (traffic quality: was the 264 even US buyers?)
  3. begin_checkout by date (clean-vs-dirty cutoff was 2026-11-16)
"""
import json
import os
import urllib.request
import urllib.parse

ENV = {}
with open("/home/jason/shopify-admin/.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            ENV[k.strip()] = v.strip()

CID = ENV["GOOGLE_CLIENT_ID"]
SEC = ENV["GOOGLE_CLIENT_SECRET"]
REF = ENV["GOOGLE_REFRESH_TOKEN"]
PROP = "313397200"

tok = json.load(urllib.request.urlopen(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({
        "client_id": CID, "client_secret": SEC,
        "refresh_token": REF, "grant_type": "refresh_token",
    }).encode(),
))["access_token"]


def run(body):
    req = urllib.request.Request(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}:runReport",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GA4 {e.code}: {e.read().decode()[:800]}\nBODY={json.dumps(body)[:400]}")


D1, D2 = "2026-11-01", "2026-11-16"

rep1 = run({
    "dateRanges": [{"startDate": D1, "endDate": D2}],
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "activeUsers"}, {"name": "eventCount"}],
    "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {"values": [
        "add_to_cart", "begin_checkout", "add_shipping_info", "add_payment_info", "purchase",
    ]}}},
})
print("== 1) funnel events (users / events) ==")
for row in rep1.get("rows", []):
    print(f"  {row['dimensionValues'][0]['value']:<22} users={row['metricValues'][0]['value']:>5}  events={row['metricValues'][1]['value']:>6}")

rep2 = run({
    "dateRanges": [{"startDate": D1, "endDate": D2}],
    "dimensions": [{"name": "country"}],
    "metrics": [{"name": "activeUsers"}, {"name": "eventCount"}],
    "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {"values": ["begin_checkout"]}}},
})
print("\n== 2) begin_checkout by country ==")
for row in rep2.get("rows", []):
    print(f"  {row['dimensionValues'][0]['value']:<30} users={row['metricValues'][0]['value']:>5}  events={row['metricValues'][1]['value']:>6}")

rep3 = run({
    "dateRanges": [{"startDate": D1, "endDate": D2}],
    "dimensions": [{"name": "date"}],
    "metrics": [{"name": "activeUsers"}, {"name": "eventCount"}],
    "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {"values": ["begin_checkout"]}}},
})
print("\n== 3) begin_checkout by date ==")
for row in rep3.get("rows", []):
    print(f"  {row['dimensionValues'][0]['value']}  users={row['metricValues'][0]['value']:>4}  events={row['metricValues'][1]['value']:>5}")
