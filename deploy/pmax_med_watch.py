# -*- coding: utf-8 -*-
"""PMax Medical Estry 商品池恢复监控（可重复跑）：
A) 商品级流量按日（imp>0 即商品池恢复铁证）
B) product_group_view（树节点级投放状态）
C) campaign 按日总指标（花费形态）
结论行：商品池已恢复 / 仍未恢复
"""
import os
from collections import defaultdict

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID = "7059800494"
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
        print("GAQL error:", r.status_code, r.text[:500])
        return []
    return [row for batch in r.json() for row in batch.get("results", [])]


print("=" * 24, "A) 商品级流量近7天(imp>0=恢复)", "=" * 24)
rows = gaql("""
    SELECT campaign.id, segments.date, metrics.impressions,
      metrics.clicks, metrics.cost_micros
    FROM shopping_performance_view
    WHERE campaign.id = 24441391608 AND segments.date DURING LAST_7_DAYS""")
daily = defaultdict(lambda: [0, 0, 0.0])
for r in rows:
    d = r["segments"]["date"]
    m = r["metrics"]
    e = daily[d]
    e[0] += int(m.get("impressions", 0))
    e[1] += int(m.get("clicks", 0))
    e[2] += float(m.get("costMicros", 0)) / 1e6
if daily:
    for d in sorted(daily):
        i, c, cost = daily[d]
        print(f"- {d}: imp={i} clicks={c} cost={cost:.2f}")
else:
    print("- (仍无任何商品级流量)")

print("\n" + "=" * 24, "B) product_group_view(树节点投放)", "=" * 24)
rows = gaql("""
    SELECT campaign.id, metrics.impressions, metrics.clicks,
      metrics.cost_micros
    FROM product_group_view
    WHERE campaign.id = 24441391608""")
if rows:
    for r in rows:
        m = r["metrics"]
        print(f"- imp={m.get('impressions', 0)} clicks={m.get('clicks', 0)} "
              f"cost={float(m.get('costMicros', 0))/1e6:.2f}")
else:
    print("- (无节点投放记录=商品池仍为空)")

print("\n" + "=" * 24, "C) campaign 按日总指标近3天", "=" * 24)
rows = gaql("""
    SELECT campaign.id, segments.date, metrics.impressions,
      metrics.clicks, metrics.cost_micros
    FROM campaign
    WHERE campaign.id = 24441391608 AND segments.date DURING LAST_3_DAYS""")
for r in rows:
    d = r["segments"]["date"]
    m = r["metrics"]
    print(f"- {d}: imp={m.get('impressions', 0)} clicks={m.get('clicks', 0)} "
          f"cost={float(m.get('costMicros', 0))/1e6:.2f}")

shop_ok = bool(daily) and any(v[0] > 0 for v in daily.values())
pg_ok = bool(rows)
print("\n结论:", "✅ 商品池已恢复（有商品在投）"
      if (shop_ok or pg_ok) else
      "❌ 商品池未恢复（MC 审核中或仍有批量被拒——属预期窗口内）")
