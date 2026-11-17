# -*- coding: utf-8 -*-
"""P0-1 转化动作治理：
- 真实购买类(Google Shopping App Purchase) → primary_for_goal=True
- 微事件(PageView/Search/ViewItem/AddToCart/BeginCheckout/AddPaymentInfo,
  含 2021 旧 app 同类) → primary_for_goal=False
- 死数据源(UA Transactions / 2021 旧 Feed app Purchase / GA4浏览超1分钟primary)
  → REMOVE 或 primary=False
- 其余(REMOVED/HIDDEN)不动
先查全量，按规则逐个 mutate，最后复查打印终态。
"""
import os

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

BASE = "https://googleads.googleapis.com/v25"


def gaql(query):
    r = httpx.post(f"{BASE}/customers/{CID}/googleAds:searchStream",
                   headers=H, json={"query": query}, timeout=90)
    r.raise_for_status()
    return [row for batch in r.json() for row in batch.get("results", [])]


rows = gaql("""
    SELECT conversion_action.resource_name, conversion_action.name,
      conversion_action.type, conversion_action.status,
      conversion_action.category, conversion_action.primary_for_goal
    FROM conversion_action""")

# ---- 变更规则（按名字精确匹配）----
PRIMARY_TRUE = {"Google Shopping App Purchase"}          # 真购买，计入出价
PRIMARY_FALSE = {                                         # 微事件，仅记录
    "Google Shopping App Page View", "Google Shopping App Search",
    "Google Shopping App View Item", "Google Shopping App Add To Cart",
    "Google Shopping App Begin Checkout",
    "Google Shopping App Add Payment Info",
    "Begin Checkout Feed For Google Shopping app #20210810154214",
    "bomibattery - GA4 (web) 浏览超1分钟",
}
REMOVE = {                                                # 死数据源
    "Transactions (全部网站数据)",           # UA 已停
    "Feed For Google Shopping app Purchase #20210810154214",  # 2021旧app
}

ops = []
for r in rows:
    a = r["conversionAction"]
    nm, rn = a["name"], a["resourceName"]
    st, pf = a.get("status"), a.get("primaryForGoal")
    if nm in PRIMARY_TRUE and not pf:
        ops.append((rn, nm, {"resourceName": rn, "primaryForGoal": True},
                    "primary_for_goal"))
    elif nm in PRIMARY_FALSE and pf:
        ops.append((rn, nm, {"resourceName": rn, "primaryForGoal": False},
                    "primary_for_goal"))
    elif nm in REMOVE and st != "REMOVED":
        ops.append((rn, nm, {"resourceName": rn, "status": "REMOVED"},
                    "status"))

print(f"计划变更 {len(ops)} 项：")
for rn, nm, upd, mask in ops:
    print(f"  - {nm}: {mask} -> {upd.get('primaryForGoal', upd.get('status'))}")

for rn, nm, upd, mask in ops:
    body = {"operations": [{"update": upd, "updateMask": mask}]}
    r = httpx.post(f"{BASE}/customers/{CID}/conversionActions:mutate",
                   headers=H, json=body, timeout=60)
    ok = r.status_code == 200
    print(("OK  " if ok else "FAIL") + f" {nm}: {r.text[:200] if not ok else ''}")

print("\n=== 复查终态 ===")
for r in gaql("""
        SELECT conversion_action.name, conversion_action.status,
          conversion_action.category, conversion_action.primary_for_goal
        FROM conversion_action"""):
    a = r["conversionAction"]
    if a.get("status") == "ENABLED" or a.get("primaryForGoal"):
        print(f"- {a['name']!r} | {a.get('status')} | "
              f"primary={a.get('primaryForGoal')}")
