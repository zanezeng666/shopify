# -*- coding: utf-8 -*-
"""补刀确认：① PMax 43 个"转化"按动作拆分定性 ② 含 REMOVED 的全 campaign 花费
③ shopping_performance_view 商品池真实投放。"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
API = "https://googleads.googleapis.com/v26/customers/7059800494"
D1, D2 = "2026-11-01", "2026-11-15"


def ga(q):
    r = httpx.post(f"{API}/googleAds:searchStream",
                   headers=H, json={"query": q}, timeout=60)
    if r.status_code != 200:
        print(f"  [HTTP {r.status_code}] {r.text[:150]}")
        return []
    j = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for b in j:
        out += b.get("results", [])
    return out


print("=== A) PMax Medical 转化按动作拆分 ===")
for e in ga(
        "SELECT conversion_action.name, conversion_action.category, "
        "metrics.conversions, metrics.clicks, metrics.cost_micros "
        "FROM campaign "
        f"WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
        "AND campaign.name LIKE '%Medical%' ORDER BY metrics.conversions DESC"):
    a, m = e["conversionAction"], e.get("metrics", {})
    n = float(m.get("conversions", 0))
    if n or int(m.get("costMicros", 0)):
        print(f"   转化{n:>5.0f}  {a['name'][:44]:<44} cat={a.get('category','')[:16]:<16}"
              f" 点击{m.get('clicks',0):>5} 花${int(m.get('costMicros',0))/1e6:.2f}")

print("\n=== B) 全部 campaign（含 REMOVED/PAUSED）11 月花费 ===")
for e in ga(
        "SELECT campaign.name, campaign.status, "
        "metrics.cost_micros, metrics.clicks, metrics.conversions "
        "FROM campaign "
        f"WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
        "ORDER BY metrics.cost_micros DESC"):
    c, m = e["campaign"], e.get("metrics", {})
    cost = int(m.get("costMicros", 0)) / 1e6
    if cost >= 1:
        print(f"   [{c.get('status','?'):>8}] {c['name'][:42]:<42}"
              f" 花${cost:>7.2f} 点击{m.get('clicks',0):>5} 转化{float(m.get('conversions',0)):>4.0f}")

print("\n=== C) 商品池投放（shopping view 全渠道） ===")
rows = ga(
    "SELECT segments.product_title, metrics.clicks, metrics.impressions, "
    "metrics.cost_micros FROM shopping_performance_view "
    f"WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
    "ORDER BY metrics.clicks DESC LIMIT 12")
for e in rows:
    m = e.get("metrics", {})
    print(f"   点击{m.get('clicks',0):>4} 曝光{int(m.get('impressions',0)):>8,}"
          f" ${(int(m.get('costMicros',0))/1e6):>6.2f}  "
          f"{(e['segments'].get('productTitle') or '')[:52]}")
if not rows:
    print("   (无数据)")
