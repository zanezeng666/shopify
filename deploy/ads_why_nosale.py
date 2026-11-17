# -*- coding: utf-8 -*-
"""零出单诊断（Ads 花费侧）：
① 三账号 campaign 11-01~15 实际花费/点击/转化
② 主账号转化动作配置（智能出价的信号源）
③ PMax asset_group + 商品池(shopping_performance_view)
④ PMax 搜索词花费 TOP20
"""
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
API = "https://googleads.googleapis.com/v26/customers"
MAIN = "7059800494"
D1, D2 = "2026-11-01", "2026-11-15"


def ga(cid, q):
    r = httpx.post(f"{API}/{cid}/googleAds:searchStream",
                   headers=H, json={"query": q}, timeout=60)
    if r.status_code != 200:
        print(f"  [HTTP {r.status_code}] {r.text[:200]}")
        return []
    j = r.json() if isinstance(r.json(), list) else [r.json()]
    out = []
    for b in j:
        out += b.get("results", [])
    return out


print("=== 1) campaign 花费 (11-01~11-15, 三账号) ===")
tot = {"cost": 0.0, "clicks": 0, "imps": 0, "conv": 0.0}
for cid in (MAIN, "2214926660", "1651348739"):
    rows = ga(cid, (
        "SELECT campaign.name, campaign.status, campaign.advertising_channel_type, "
        "metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.conversions, "
        "metrics.average_cpc "
        f"FROM campaign WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
        "AND campaign.status != 'REMOVED' ORDER BY metrics.cost_micros DESC"))
    if not rows:
        print(f"-- 账号 {cid}: 无数据")
        continue
    print(f"-- 账号 {cid}")
    for e in rows:
        c, m = e["campaign"], e.get("metrics", {})
        cost = int(m.get("costMicros", 0)) / 1e6
        tot["cost"] += cost
        tot["clicks"] += int(m.get("clicks", 0))
        tot["imps"] += int(m.get("impressions", 0))
        tot["conv"] += float(m.get("conversions", 0))
        if cost > 0 or int(m.get("clicks", 0)):
            print(f"   {c['name'][:40]:<40} {c['advertisingChannelType'][:12]:<12}"
                  f" 花${cost:>7.2f} 点击{m.get('clicks',0):>5}"
                  f" 曝光{int(m.get('impressions',0)):>9,} 转化{m.get('conversions',0):>4}"
                  f" CPC${int(m.get('averageCpc',0))/1e6:.2f}")
print(f"合计: 花${tot['cost']:.2f} 点击{tot['clicks']} 曝光{tot['imps']:,} 转化{tot['conv']}")

print("\n=== 2) 转化动作配置 (主账号) ===")
rows = ga(MAIN, (
    "SELECT conversion_action.name, conversion_action.status, "
    "conversion_action.category, conversion_action.primary_for_goal, "
    "conversion_action.counting_type, conversion_action.origin "
    "FROM conversion_action"))
if not rows:
    print("  ★无转化动作（智能出价零信号！）")
for e in rows:
    a = e["conversionAction"]
    print(f"   [{a.get('status'):>8}] {a['name'][:34]:<34}"
          f" cat={a.get('category','')[:14]:<14} origin={a.get('origin','')[:10]:<10}"
          f" primary={a.get('primaryForGoal')}")

print("\n=== 3) PMax asset_group (主账号) ===")
rows = ga(MAIN, (
    "SELECT campaign.name, asset_group.name, asset_group.status, "
    "metrics.cost_micros, metrics.clicks, metrics.conversions "
    "FROM asset_group WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX' "
    f"AND segments.date BETWEEN '{D1}' AND '{D2}' "
    "ORDER BY metrics.cost_micros DESC"))
for e in rows:
    g, m = e["assetGroup"], e.get("metrics", {})
    print(f"   [{g.get('status'):>7}] {g['name'][:28]:<28} @ {e['campaign']['name'][:22]:<22}"
          f" 花${int(m.get('costMicros',0))/1e6:>7.2f} 点击{m.get('clicks',0):>4}"
          f" 转化{m.get('conversions',0)}")
if not rows:
    print("   (无)")

print("\n=== 3b) PMax 商品池真实投放 (shopping_performance_view) ===")
rows = ga(MAIN, (
    "SELECT segments.product_title, segments.product_item_id, "
    "metrics.clicks, metrics.impressions, metrics.cost_micros "
    "FROM shopping_performance_view WHERE campaign.advertising_channel_type = 'PERFORMANCE_MAX' "
    f"AND segments.date BETWEEN '{D1}' AND '{D2}' "
    "ORDER BY metrics.clicks DESC LIMIT 15"))
for e in rows:
    m = e.get("metrics", {})
    print(f"   点击{m.get('clicks',0):>4} 曝光{int(m.get('impressions',0)):>8,}"
          f" ${(int(m.get('costMicros',0))/1e6):>6.2f}"
          f"  {e['segments'].get('productTitle','')[:48]}")
if not rows:
    print("   ★商品池零曝光——商品根本没在投！")

print("\n=== 4) PMax 搜索词花费 TOP20 (主账号) ===")
rows = ga(MAIN, (
    "SELECT campaign.name, campaign_search_term_view.search_term, "
    "metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.conversions "
    "FROM campaign_search_term_view "
    f"WHERE segments.date BETWEEN '{D1}' AND '{D2}' "
    "ORDER BY metrics.cost_micros DESC LIMIT 20"))
for e in rows:
    m = e.get("metrics", {})
    print(f"   花${int(m.get('costMicros',0))/1e6:>6.2f} 点击{m.get('clicks',0):>3}"
          f" 转化{m.get('conversions',0)}"
          f"  [{e['campaign']['name'][:16]}] {e['campaignSearchTermView']['searchTerm'][:44]}")
if not rows:
    print("   (无)")
