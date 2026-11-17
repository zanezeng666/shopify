# -*- coding: utf-8 -*-
"""MC 免费 listing：v2.1 freelistingsprogram 完整 body + Merchant API 探测
+ productstatuses issue 描述修正统计（趁端点可用）。"""
import os
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}"}

# 1) v2.1 freelistingsprogram 完整 body
r = httpx.get(
    f"https://shoppingcontent.googleapis.com/content/v2.1/{MID}"
    "/freelistingsprogram", headers=H, timeout=30)
print("== v2.1 freelistingsprogram", r.status_code, "==")
print(r.text[:800])

# 2) Merchant API programs 列表
for base in (
        f"https://merchantapi.googleapis.com/programs/v1beta/accounts/{MID}/programs",
        f"https://merchantapi.googleapis.com/programs/v1/accounts/{MID}/programs"):
    p = httpx.get(base, headers=H, timeout=30)
    print(f"\n== Merchant API programs {base.split('googleapis.com')[1]} "
          f"-> {p.status_code} ==")
    if p.status_code == 200:
        print(p.text[:1200])
        break
    print(p.text[:200])

# 3) Merchant API freeListings 单独资源探测
for u in (
        f"https://merchantapi.googleapis.com/programs/v1beta/accounts/{MID}/programs/freeListings",
        f"https://merchantapi.googleapis.com/programs/v1beta/accounts/{MID}/programs/free-listings"):
    p = httpx.get(u, headers=H, timeout=30)
    print(f"\nfreeListings probe {u.rsplit('/', 1)[-1]}: {p.status_code} "
          f"{p.text[:300] if p.status_code != 404 else ''}")

# 4) productstatuses issue 描述修正（字段=description）
stats, issues, tok, total = Counter(), Counter(), None, 0
while True:
    params = {"maxResults": 250}
    if tok:
        params["pageToken"] = tok
    p = httpx.get(
        f"https://shoppingcontent.googleapis.com/content/v2.1/{MID}"
        "/productstatuses", headers=H, params=params, timeout=60)
    if p.status_code != 200:
        print(f"\nproductstatuses 终止于 page(total={total}):",
              p.status_code)
        break
    for it in p.json().get("resources", []):
        total += 1
        for ils in it.get("itemLevelIssues", []):
            serv = ils.get("servability", "")
            stats[serv] += 1
            if serv not in ("unaffected", "disapproved"):
                continue
            if serv == "disapproved":
                issues[ils.get("description", ils.get("code", "?"))] += 1
    tok = p.json().get("nextPageToken")
    if not tok:
        break
print(f"\nSKU 状态条目: {total}")
print("servability:", dict(stats))
print("disapproved 原因 top10:")
for t, n in issues.most_common(10):
    print(f"  {t} x{n}")
