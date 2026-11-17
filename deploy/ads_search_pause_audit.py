# -*- coding: utf-8 -*-
"""审计全部 Search 系列：状态/预算/近7日花费，输出停投建议名单。只读。"""
import os

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"

gac = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = gac.get_service("GoogleAdsService")

# 全部 SEARCH 系列（含 PAUSED，无 metrics）
all_c = {}
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, campaign.name, campaign.status "
    "FROM campaign WHERE campaign.advertising_channel_type = 'SEARCH'"))
for r in rows:
    all_c[r.campaign.id] = (r.campaign.name, r.campaign.status.name, 0)

# 近 7 日花费
spend = {}
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.id, metrics.cost_micros, metrics.clicks, "
    "metrics.conversions FROM campaign "
    "WHERE campaign.advertising_channel_type = 'SEARCH' "
    "AND segments.date BETWEEN '2026-11-10' AND '2026-11-16'"))
for r in rows:
    spend[r.campaign.id] = (r.metrics.cost_micros / 1e6, r.metrics.clicks,
                            r.metrics.conversions)

# 医疗关键词判定（系列名含这些词=保留）
MEDICAL_TOKENS = ("Medical", "Patient Monitor", "Oximeter", "Infusion",
                  "Pump", "Defibrillator", "ECG", "Vital", "Ultrasound",
                  "Sphygmomanometer", "Medical Battery")

print(f"共 {len(all_c)} 个 SEARCH 系列\n")
tot_cost = tot_clicks = 0.0
keep, pause = [], []
for cid, (name, st, bud) in sorted(all_c.items(),
                                   key=lambda x: -spend.get(x[0], (0,))[0]):
    cost, clicks, conv = spend.get(cid, (0.0, 0, 0.0))
    is_med = any(t in name for t in MEDICAL_TOKENS)
    (keep if is_med else pause).append((cid, name, st, bud, cost, clicks))
    tot_cost += cost
    tot_clicks += clicks
    flag = "保留" if is_med else "停投"
    print(f"  [{flag}] {name[:40]:<40} {st:<8} 日预算${bud:<7.2f} "
          f"近7日${cost:<7.2f} clicks={clicks}")

print(f"\n近 7 日 Search 总花费 ${tot_cost:.2f}，总点击 {tot_clicks}")
pk = sum(x[4] for x in keep)
pc = sum(x[4] for x in pause)
print(f"  保留（医疗）{len(keep)} 个：${pk:.2f}")
print(f"  建议停投 {len(pause)} 个：${pc:.2f}（日均 ${pc/7:.1f}）")
print("\nPAUSE 名单（id|name）：")
for cid, name, st, bud, cost, clicks in pause:
    if st == "ENABLED":
        print(f"  {cid}|{name}")
