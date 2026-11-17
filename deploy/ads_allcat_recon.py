# -*- coding: utf-8 -*-
"""各分类搜索广告侦察（只读）：
1. Ads 账户币种/现有campaign/出价策略/callout资产
2. 镜像库 active 产品分类分布 + 每分类Top品牌(变体SKU段)
3. Shopify collections 落地页现状
4. cs_new.device 表各分类挖词覆盖
"""
import os
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
    return r.json().get("rows") or []


print("=== 1. 账户 ===")
for row in query("SELECT customer.descriptive_name, customer.currency_code, "
                 "customer.time_zone FROM customer"):
    c = row["customer"]
    print(f"{c['descriptiveName']} | 币种={c['currencyCode']} | "
          f"时区={c['timeZone']}")

print("\n=== 2. 现有 campaigns ===")
for row in query(
    "SELECT campaign.name, campaign.status, "
    "campaign.advertising_channel_type, campaign.bidding_strategy_type, "
    "campaign_budget.amount_micros, campaign_budget.explicitly_shared "
    "FROM campaign ORDER BY campaign.name"):
    c, b = row["campaign"], row["campaignBudget"]
    amt = int(b["amountMicros"]) / 1_000_000
    print(f"[{c['status']:8}] {c['advertisingChannelType']:12} "
          f"{c['name'][:44]:44} 预算={amt:g} 共享={b['explicitlyShared']} "
          f"出价={c['biddingStrategyType']}")

print("\n=== 3. 组合出价策略 ===")
for row in query(
    "SELECT bidding_strategy.resource_name, bidding_strategy.name, "
    "bidding_strategy.type FROM bidding_strategy"):
    b = row["biddingStrategy"]
    print(f"{b['name']} | {b['type']} | {b['resourceName']}")

print("\n=== 4. callout 资产 ===")
for row in query("SELECT asset.resource_name, asset.callout_asset.callout_text "
                 "FROM asset WHERE asset.type='CALLOUT'"):
    a = row["asset"]
    print(f"  {(a.get('calloutAsset') or {}).get('calloutText')}")

print("\n=== 5. 镜像 active 产品分类分布+Top品牌 ===")
from shopify_admin.core.database import get_engine  # noqa: E402
with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT p.product_type, SUBSTRING_INDEX(pv.sku, '_', 2) sku2
        FROM products p JOIN product_variants pv ON pv.product_id = p.id
        WHERE p.store_id = 1 AND p.status = 'active' AND pv.sku LIKE 'CS-%'
    """)).fetchall()
cat_brands = defaultdict(Counter)
cat_variants = Counter()
for ptype, sku2 in rows:
    parts = sku2.split("_")
    brand = parts[1] if len(parts) >= 2 else ""
    cat_brands[ptype or "(空)"][brand] += 1
    cat_variants[ptype or "(空)"] += 1
for cat, n in cat_variants.most_common():
    tops = ", ".join(f"{b}:{c}" for b, c in cat_brands[cat].most_common(4))
    print(f"{n:5} | {cat:40} | {tops}")

print("\n=== 6. Shopify collections ===")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
client = StoreService().get_client(1)
since = 0
while True:
    batch = client.request("GET", "collections.json", params={
        "limit": 250, "since_id": since}).get("collections", [])
    if not batch:
        break
    for coll in batch:
        print(f"  {coll['id']} [{coll.get('published_at') and 'PUB' or 'unp'}] "
              f"{coll['title'][:48]:48} /collections/{coll['handle']}")
    since = batch[-1]["id"]
client.close()

print("\n=== 7. cs_new.device 各分类覆盖 ===")
from shopify_admin.core.database import get_cs_engine  # noqa: E402
with get_cs_engine().connect() as c:
    rows = c.execute(text(
        "SELECT category, COUNT(DISTINCT cs_id), COUNT(DISTINCT brand) "
        "FROM device WHERE brand IS NOT NULL AND brand <> '' "
        "AND device_model IS NOT NULL AND device_model <> '' "
        "GROUP BY category ORDER BY COUNT(DISTINCT cs_id) DESC LIMIT 40"
    )).fetchall()
for cat, ncs, nb in rows:
    print(f"  device {ncs:5} csid {nb:4} 品牌 | {cat}")
