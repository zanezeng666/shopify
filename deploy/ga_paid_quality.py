# -*- coding: utf-8 -*-
"""零出单诊断（GA4 流量质量侧 + Shopify 订单交叉验证）：
① 付费渠道 engagement/关键事件
② 付费流量落地页 TOP（找 404/烂页）
③ 全站事件计数（generate_lead 询盘是 B2B 主转化）
④ 付费流量国家分布
⑤ Shopify 11-01 以来真实订单（绕开归因，看全店事实）
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
PROP = "313397200"
API = f"https://analyticsdata.googleapis.com/v1beta/properties/{PROP}"

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
DR = [{"startDate": "2026-11-01", "endDate": "2026-11-15"}]
PAID = {"inListFilter": {"values": ["Paid Search", "Cross-network", "Paid Shopping"]}}


def run(body):
    r = httpx.post(f"{API}:runReport", json=body, headers=H, timeout=120)
    if r.status_code != 200:
        print(f"  GA4 {r.status_code}: {r.text[:200]}")
        return []
    return r.json().get("rows", [])


def show(rows, note=""):
    if not rows:
        print("  (无数据)")
        return
    for r in rows:
        print("  " + " | ".join(
            dv["value"] for dv in r["dimensionValues"]) + " | " +
            " | ".join(f"{mv['value'][:12]}" for mv in r["metricValues"]) + note * 0)


print("=== 1) 付费渠道质量 (11-01~15) ===")
show(run({
    "dateRanges": DR,
    "dimensions": [{"name": "sessionDefaultChannelGroup"}],
    "metrics": [{"name": "sessions"}, {"name": "engagementRate"},
                {"name": "keyEvents"}, {"name": "ecommercePurchases"}],
    "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup", **PAID}},
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
}))

print("\n=== 2) 付费流量落地页 TOP15 ===")
show(run({
    "dateRanges": DR,
    "dimensions": [{"name": "landingPagePath"}],
    "metrics": [{"name": "sessions"}, {"name": "engagementRate"},
                {"name": "keyEvents"}],
    "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup", **PAID}},
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    "limit": 15,
}))

print("\n=== 3) 全站事件计数（询盘/搜索/加购/结账） ===")
show(run({
    "dateRanges": DR,
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "eventCount"}],
    "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
    "limit": 15,
}))

print("\n=== 4) 付费流量国家 TOP10 ===")
show(run({
    "dateRanges": DR,
    "dimensions": [{"name": "country"}],
    "metrics": [{"name": "sessions"}, {"name": "keyEvents"}],
    "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup", **PAID}},
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    "limit": 10,
}))

print("\n=== 5) Shopify 11-01 以来真实订单（全渠道事实） ===")
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client
q = ("query{orders(first:50,query:\"created_at:>=2026-11-01\"){edges{node{"
     "name createdAt displayFinancialStatus"
     " totalPriceSet{shopMoney{amount}}"
     " channel:app{name}}}}}")
r = c.graphql(q, {})
edges = ((r or {}).get("orders") or {}).get("edges") or []
print(f"订单数={len(edges)}")
for e in edges:
    n = e["node"]
    amt = ((n.get("totalPriceSet") or {}).get("shopMoney") or {}).get("amount", "?")
    ch = ((n.get("channel") or {}) or {}).get("name", "-")
    print(f"  {n['name']} {n['createdAt'][:16]} ${amt} {n.get('displayFinancialStatus')} via {ch}")
