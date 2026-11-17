# -*- coding: utf-8 -*-
"""P0-1 补丁：剩余漏项治理。
- 'Add To Cart Feed...#2021'(漏网微事件) / 'Feed...Purchase #2021' /
  'Transactions (UA)' 三个动作统一 primary_for_goal=False
（status REMOVE 被 API 拒绝，降级方案：确保不计入出价目标即可）
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


TARGETS = {
    "Add To Cart Feed For Google Shopping app #20210810154214",
    "Feed For Google Shopping app Purchase #20210810154214",
    "Transactions (全部网站数据)",
}
rows = gaql("""
    SELECT conversion_action.resource_name, conversion_action.name,
      conversion_action.primary_for_goal
    FROM conversion_action""")
for r in rows:
    a = r["conversionAction"]
    if a["name"] not in TARGETS or not a.get("primaryForGoal"):
        continue
    resp = httpx.post(
        f"{BASE}/customers/{CID}/conversionActions:mutate", headers=H,
        json={"operations": [{"update": {
            "resourceName": a["resourceName"],
            "primaryForGoal": False}, "updateMask": "primary_for_goal"}]},
        timeout=60)
    print(("OK  " if resp.status_code == 200 else "FAIL")
          + f" {a['name']}" + ("" if resp.status_code == 200
                               else ": " + resp.text[:250]))

print("\n=== 终态(仅 ENABLED/primary) ===")
final = gaql("""
    SELECT conversion_action.name, conversion_action.status,
      conversion_action.primary_for_goal
    FROM conversion_action""")
n_primary = 0
for r in sorted(final, key=lambda x: x["conversionAction"]["name"]):
    a = r["conversionAction"]
    if a.get("status") == "ENABLED" and a.get("primaryForGoal"):
        n_primary += 1
        print(f"- PRIMARY: {a['name']!r}")
print(f"\nprimary=True 的动作共 {n_primary} 个")
