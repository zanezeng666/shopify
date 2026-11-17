"""Verify the 2 purchases: which gateway, when, how much. Plus GA4 purchase by date."""
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

# ---- GA4: purchase & add_payment_info by date + country ----
tok = json.load(urllib.request.urlopen(
    "https://oauth2.googleapis.com/token",
    data=urllib.parse.urlencode({
        "client_id": ENV["GOOGLE_CLIENT_ID"], "client_secret": ENV["GOOGLE_CLIENT_SECRET"],
        "refresh_token": ENV["GOOGLE_REFRESH_TOKEN"], "grant_type": "refresh_token",
    }).encode(),
))["access_token"]


def run(body):
    req = urllib.request.Request(
        "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
    )
    try:
        return json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GA4 {e.code}: {e.read().decode()[:500]}")


for dim, ev in [("date", "purchase"), ("country", "purchase"), ("date", "add_payment_info")]:
    rep = run({
        "dateRanges": [{"startDate": "2026-11-01", "endDate": "2026-11-16"}],
        "dimensions": [{"name": dim}],
        "metrics": [{"name": "activeUsers"}, {"name": "eventCount"}],
        "dimensionFilter": {"filter": {"fieldName": "eventName", "inListFilter": {"values": [ev]}}},
    })
    print(f"== {ev} by {dim} ==")
    for row in rep.get("rows", []):
        m = row["metricValues"]
        print(f"  {row['dimensionValues'][0]['value']:<16} users={m[0]['value']:>3} events={m[1]['value']:>3}")
    print()

# ---- Shopify: recent orders with gateway ----
import sys
sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores import StoreService

client = StoreService().get_client(1)
orders = client.request("GET", "orders.json", params={
    "status": "any", "limit": 5, "fields": "id,created_at,total_price,financial_status,gateway,payment_names,name",
})
print("== Shopify recent orders ==")
for o in orders.get("orders", []):
    print(f"  {o.get('name')}  {o.get('created_at')}  ${o.get('total_price')}  {o.get('financial_status')}  gateway={o.get('gateway')}  methods={o.get('payment_names')}")
if not orders.get("orders"):
    print("  (no orders)")
