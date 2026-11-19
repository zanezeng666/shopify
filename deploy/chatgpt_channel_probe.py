"""ChatGPT 渠道识别探查：GA4 流量（sessionSource 含 chatgpt）+ Shopify 全量订单（landing_site utm）"""
import json
import os
import sys
import urllib.request
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

for line in open("/home/jason/shopify-admin/.env"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        os.environ.setdefault(k, v.strip().strip('"'))

import httpx

BJ = timezone(timedelta(hours=8))
now_bj = datetime.now(BJ)
D0 = (now_bj - timedelta(days=45)).strftime("%Y-%m-%d")
D1 = now_bj.strftime("%Y-%m-%d")

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}
URL = "https://analyticsdata.googleapis.com/v1beta/properties/313397200:runReport"
CHAT = {"filter": {"fieldName": "sessionSource",
                   "stringFilter": {"value": "chatgpt", "matchType": "CONTAINS"}}}


def rep(tag, body, show=15):
    j = httpx.post(URL, headers=H, json=body, timeout=60).json()
    rows = j.get("rows") or []
    print(f"[{tag}]" if rows else f"[{tag}] 无数据 rowCount={j.get('rowCount', 0)}")
    for row in rows[:show]:
        vals = [d["value"] for d in row["dimensionValues"]] + [m["value"] for m in row["metricValues"]]
        print("  " + " | ".join(vals))
    print()


DR = {"dateRanges": [{"startDate": D0, "endDate": D1}]}

print(f"===== A. GA4 ChatGPT 来源流量（近45天 {D0}~{D1}，sessionSource CONTAINS chatgpt）=====\n")
rep("来源×媒介 会话/用户", {**DR, "dimensions": [{"name": "sessionSource"}, {"name": "sessionMedium"}],
    "metrics": [{"name": "sessions"}, {"name": "activeUsers"}, {"name": "engagedSessions"}],
    "dimensionFilter": CHAT})
rep("按日趋势 会话", {**DR, "dimensions": [{"name": "date"}],
    "metrics": [{"name": "sessions"}, {"name": "activeUsers"}],
    "dimensionFilter": CHAT, "orderBys": [{"dimension": {"name": "date"}}]}, show=50)
rep("落地页 会话", {**DR, "dimensions": [{"name": "landingPagePlusQueryString"}],
    "metrics": [{"name": "sessions"}], "dimensionFilter": CHAT,
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}]})
rep("国家 会话", {**DR, "dimensions": [{"name": "country"}],
    "metrics": [{"name": "sessions"}, {"name": "engagedSessions"}], "dimensionFilter": CHAT,
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}]})
rep("行为事件分布", {**DR, "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "eventCount"}, {"name": "eventValue"}], "dimensionFilter": CHAT,
    "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}]})
rep("purchase（按日）", {**DR, "dimensions": [{"name": "date"}, {"name": "sessionMedium"}],
    "metrics": [{"name": "eventCount"}, {"name": "eventValue"}],
    "dimensionFilter": {"andGroup": {"expressions": [CHAT, {"filter": {
        "fieldName": "eventName", "stringFilter": {"value": "purchase"}}}]}},
    "orderBys": [{"dimension": {"name": "date"}}]})

print("===== B. Shopify 全量订单：landing_site 带 chatgpt/openai 标记 =====\n")
sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores import StoreService

client = StoreService().get_client(1)
all_orders, since_id = [], 0
while True:
    page = client.request("GET", "orders.json", params={
        "status": "any", "limit": 250, "since_id": since_id,
        "fields": "id,name,created_at,total_price,financial_status,cancelled_at,landing_site,referring_site",
    }).get("orders", [])
    all_orders.extend(page)
    if len(page) < 250:
        break
    since_id = page[-1]["id"]

hits = []
for o in all_orders:
    ls = (o.get("landing_site") or "").lower()
    rs = (o.get("referring_site") or "").lower()
    if "chatgpt" in ls or "openai" in ls or "chatgpt" in rs or "openai" in rs:
        hits.append(o)

paid = [o for o in hits if o.get("financial_status") == "paid" and not o.get("cancelled_at")]
rev = sum(float(o["total_price"]) for o in paid)
by_month = Counter(datetime.fromisoformat(o["created_at"].replace("Z", "+00:00"))
                   .astimezone(BJ).strftime("%Y-%m") for o in hits)
print(f"全量订单 {len(all_orders)} 单中，ChatGPT/OpenAI 标记 {len(hits)} 单（paid 未取消 {len(paid)} 单，¥{rev:.2f}）")
print("按月分布:", dict(sorted(by_month.items())))
for o in sorted(hits, key=lambda x: x["created_at"]):
    ts = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).astimezone(BJ)
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(o.get("landing_site") or "").query)
    camp = q.get("utm_campaign", ["-"])[0]
    med = q.get("utm_medium", ["-"])[0]
    flag = "已取消" if o.get("cancelled_at") else o.get("financial_status")
    print(f"  {o['name']}  {ts:%Y-%m-%d}  ${o['total_price']}  {flag}  medium={med} campaign={camp}")
