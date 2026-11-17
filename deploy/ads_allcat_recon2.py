# -*- coding: utf-8 -*-
"""侦察v2（只读）：修正results键+collections端点+远端active口径。"""
import json
import os
import time
from collections import Counter, defaultdict

import httpx
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
API = f"https://googleads.googleapis.com/v25/customers/{CID}"
H = {"Content-Type": "application/json", "developer-token": "unused"}


def token():
    return httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30).json()["access_token"]


def query(gaql):
    r = httpx.post(f"{API}/googleAds:search",
                   headers={**H, "Authorization": f"Bearer {token()}"},
                   json={"query": gaql}, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GAQL HTTP{r.status_code}: {r.text[:400]}")
    d = r.json()
    return d.get("results") or d.get("rows") or []


print("=== 1. 账户 ===")
for row in query("SELECT customer.descriptive_name, customer.currency_code, "
                 "customer.time_zone FROM customer"):
    c = row["customer"]
    print(f"{c['descriptiveName']} | 币种={c['currencyCode']} | "
          f"时区={c['timeZone']}")

print("\n=== 2. 现有 campaigns ===")
for row in query(
    "SELECT campaign.name, campaign.status, "
    "campaign.advertising_channel_type, "
    "campaign_budget.amount_micros "
    "FROM campaign ORDER BY campaign.name"):
    c, b = row["campaign"], row["campaignBudget"]
    print(f"[{c['status']:8}] {c['advertisingChannelType']:8} "
          f"{c['name'][:48]:48} 预算={int(b['amountMicros'])/1e6:g}")

print("\n=== 3. 组合出价策略 ===")
for row in query(
    "SELECT bidding_strategy.resource_name, bidding_strategy.name, "
    "bidding_strategy.type FROM bidding_strategy"):
    b = row["biddingStrategy"]
    print(f"{b['name']} | {b['type']} | {b['resourceName']}")

print("\n=== 4. callout 资产 ===")
for row in query("SELECT asset.callout_asset.callout_text FROM asset "
                 "WHERE asset.type='CALLOUT'"):
    print(f"  {(row['asset'].get('calloutAsset') or {}).get('calloutText')}")

print("\n=== 5. 远端 active 产品分类（权威口径）===")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
client = StoreService().get_client(1)
remote: dict[int, str] = {}
since = 0
while True:
    batch = client.request("GET", "products.json", params={
        "limit": 250, "status": "active", "since_id": since,
        "fields": "id,product_type"}).get("products", [])
    if not batch:
        break
    for p in batch:
        remote[int(p["id"])] = (p.get("product_type") or "").strip()
    since = batch[-1]["id"]
    time.sleep(0.35)
print(f"远端 active 产品总数: {len(remote)}")
cat_counts = Counter(remote.values())
for cat, n in cat_counts.most_common():
    print(f"{n:5} | {cat or '(空)'}")

print("\n=== 6. collections（smart+custom）===")
colls = []
for ep in ("smart_collections.json", "custom_collections.json"):
    since = 0
    while True:
        batch = client.request("GET", ep, params={
            "limit": 250, "since_id": since}).get(
                "smart_collections" if "smart" in ep else "custom_collections",
                [])
        if not batch:
            break
        colls += batch
        since = batch[-1]["id"]
        time.sleep(0.35)
by_handle = {}
for c in colls:
    by_handle[c["handle"]] = c["title"]
    print(f"  {c['id']} {'PUB' if c.get('published_at') else 'unp'} "
          f"{c['title'][:52]:52} /collections/{c['handle']}")
json.dump({k: by_handle[k] for k in by_handle},
          open("/tmp/colls.json", "w"), ensure_ascii=False)
client.close()

print("\n=== 7. 远端active分类×Top品牌（镜像join远端id）===")
from shopify_admin.core.database import get_engine  # noqa: E402
ids = list(remote)
cat_brands = defaultdict(Counter)
with get_engine().connect() as m:
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        ph = ",".join(str(x) for x in chunk)
        rows = m.execute(text(
            f"SELECT SUBSTRING_INDEX(sku, '_', 2) s2 FROM product_variants "
            f"WHERE store_id = 1 AND shopify_product_id IN ({ph}) "
            f"AND sku LIKE 'CS-%'")).fetchall()
        for (s2,) in rows:
            parts = s2.split("_")
            if len(parts) >= 2:
                cat_brands["_all_"][parts[1]] += 1
brand_out = {}
for cat, n in cat_counts.most_common(40):
    ids_cat = [i for i, c in remote.items() if c == cat]
    cb = Counter()
    with get_engine().connect() as m:
        for i in range(0, len(ids_cat), 500):
            chunk = ids_cat[i:i + 500]
            ph = ",".join(str(x) for x in chunk)
            rows = m.execute(text(
                f"SELECT SUBSTRING_INDEX(sku, '_', 2) s2 FROM product_variants "
                f"WHERE store_id = 1 AND shopify_product_id IN ({ph}) "
                f"AND sku LIKE 'CS-%'")).fetchall()
            for (s2,) in rows:
                parts = s2.split("_")
                if len(parts) >= 2:
                    cb[parts[1]] += 1
    brand_out[cat] = cb.most_common(8)
    print(f"{cat or '(空)':40} | " +
          ", ".join(f"{b}:{n}" for b, n in cb.most_common(6)))
json.dump(brand_out, open("/tmp/cat_brands.json", "w"),
          ensure_ascii=False, indent=1)

print("\n=== 8. cs_new.device 各分类覆盖 ===")
from shopify_admin.core.database import get_cs_engine  # noqa: E402
with get_cs_engine().connect() as c:
    rows = c.execute(text(
        "SELECT category, COUNT(DISTINCT cs_id), COUNT(DISTINCT brand) "
        "FROM device WHERE brand IS NOT NULL AND brand <> '' "
        "AND device_model IS NOT NULL AND device_model <> '' "
        "GROUP BY category ORDER BY COUNT(DISTINCT cs_id) DESC LIMIT 30"
    )).fetchall()
for cat, ncs, nb in rows:
    print(f"  device {ncs:5} csid {nb:4} 品牌 | {cat}")
