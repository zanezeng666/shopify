# -*- coding: utf-8 -*-
"""PMax Medical Estry 诊断 v2：C) 资产绑定状态 D) 商品分组树 E) 商品级流量"""
import os
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID = "7059800494"
AG = "6770847164"
TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {TOK}", "developer-token": "unused",
     "login-customer-id": CID}


def gaql(query):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/googleAds:searchStream",
        headers=H, json={"query": query}, timeout=90)
    if r.status_code != 200:
        print("GAQL error:", r.status_code, r.text[:1500])
        return []
    return [row for batch in r.json() for row in batch.get("results", [])]


print("=" * 20, f"C) assets of ag={AG}", "=" * 20)
rows = gaql(f"""
    SELECT asset_group_asset.asset_field_type,
      asset_group_asset.status, asset_group_asset.source,
      asset.type, asset.resource_name
    FROM asset_group_asset
    WHERE asset_group.id = {AG}""")
stat = Counter()
for r in rows:
    a = r["assetGroupAsset"]
    k = (a["assetFieldType"], a["status"])
    stat[k] += 1
    print(f"- {a['assetFieldType']:<22} {a['status']:<10} "
          f"src={a.get('source','?'):<22} {r.get('asset',{}).get('type','?')}")
print("\n状态分布:")
for (ft, st), n in sorted(stat.items()):
    print(f"  {ft:<22} {st:<10} x{n}")

print("\n" + "=" * 20, f"D) listing_group_filter tree ag={AG}", "=" * 20)
DIMS = (
    ("product_brand", "case_value.product_brand.value"),
    ("product_type", "case_value.product_type.value"),
    ("product_item", "case_value.product_item.id"),
    ("product_channel", "case_value.product_channel.channel"),
    ("product_condition", "case_value.product_condition.condition"),
    ("product_category", "case_value.product_category.category_id"),
    ("custom_attr", "case_value.product_custom_attribute.value"),
)
ok_dims = []
for label, field in DIMS:
    r2 = gaql(f"SELECT {field} FROM asset_group_listing_group_filter "
              f"WHERE asset_group.id = {AG} LIMIT 1")
    if r2:
        ok_dims.append((label, field))
    else:
        print(f"(维度不可查: {label})")
sel = ("asset_group_listing_group_filter.id, "
       "asset_group_listing_group_filter.type"
       + (", " + ", ".join(f for _, f in ok_dims) if ok_dims else ""))
rows = gaql(f"""
    SELECT {sel}
    FROM asset_group_listing_group_filter
    WHERE asset_group.id = {AG}""")
for r in rows:
    f = r["assetGroupListingGroupFilter"]
    cv = f.get("caseValue", {}) or {}
    parts = []
    for label, field in ok_dims:
        key = field.split(".")[-1]
        v = cv.get(label)
        if v:
            parts.append(f"{label}={v.get(key, v)}")
    print(f"- node={f['id']:<18} type={f['type']:<15} "
          + (" ".join(parts) if parts else "(根节点/全场)"))

print("\n" + "=" * 20, "E) shopping_performance LAST_30_DAYS", "=" * 20)
rows = gaql("""
    SELECT campaign.name, metrics.clicks, metrics.cost_micros,
      metrics.conversions, metrics.impressions
    FROM shopping_performance_view
    WHERE segments.date DURING LAST_30_DAYS""")
agg = {}
for r in rows:
    cn = r["campaign"]["name"]
    m = r["metrics"]
    d = agg.setdefault(cn, [0, 0.0, 0.0, 0])
    d[0] += int(m.get("clicks", 0))
    d[1] += float(m.get("costMicros", 0)) / 1e6
    d[2] += float(m.get("conversions", 0))
    d[3] += int(m.get("impressions", 0))
if not agg:
    print("(近30天无任何商品级流量记录)")
for cn, (clk, cost, conv, imp) in sorted(agg.items()):
    print(f"- {cn}: imp={imp} clicks={clk} cost={cost:.2f} conv={conv:g}")
