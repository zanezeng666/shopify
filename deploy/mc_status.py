# -*- coding: utf-8 -*-
"""Merchant API v1 MC 商品审批状态统计 v2
状态形状: destinationStatuses[].reportingContext + approved/disapproved/pendingCountries"""
import json
import os
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"
BASE = (f"https://merchantapi.googleapis.com/products/v1/accounts/{MID}"
        "/products")

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

CTX = "SHOPPING_ADS"  # PMax/Shopping 投放面
cnt = Counter()
issue_cnt = Counter()
samples, dis_issue_raw = [], None
page_token, total, first_dis = None, 0, True
while True:
    url = f"{BASE}?pageSize=250" + (f"&pageToken={page_token}" if page_token else "")
    r = httpx.get(url, headers=H, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"API {r.status_code}: {r.text[:300]}")
    j = r.json()
    for p in j.get("products", []):
        total += 1
        ps = p.get("productStatus") or {}
        st = "no_ctx"
        for d in ps.get("destinationStatuses", []):
            if d.get("reportingContext") == CTX:
                if "US" in (d.get("approvedCountries") or []):
                    st = "approved"
                elif "US" in (d.get("disapprovedCountries") or []):
                    st = "disapproved"
                elif "US" in (d.get("pendingCountries") or []):
                    st = "pending"
                else:
                    st = "unknown"
                break
        cnt[st] += 1
        if st == "disapproved":
            issues = [i for i in ps.get("itemLevelIssues", [])
                      if i.get("severity") != "NOT_IMPACTED"]
            for i in issues:
                issue_cnt[str(i.get("code") or i.get("issueType") or "?")] += 1
            if first_dis and issues:
                dis_issue_raw = json.dumps(issues[0], ensure_ascii=False)[:400]
                first_dis = False
            if len(samples) < 8:
                samples.append((
                    (p.get("productAttributes") or {}).get("title", "")[:36],
                    p.get("offerId", "")[:26],
                    [str(i.get("code")) for i in issues][:5]))
    page_token = j.get("nextPageToken")
    if not page_token:
        break

print(f"=== MC {MID} 在线商品总数: {total} | reportingContext={CTX} ===")
for s, c in cnt.most_common():
    print(f"  {s:14s} {c:5d}  ({c*100//max(total,1)}%)")
if dis_issue_raw:
    print("\n侦察-disapproved issue 原始形状:", dis_issue_raw)
print("\ndisapproved 拒因 Top12:")
for iss, c in issue_cnt.most_common(12):
    print(f"  {iss:40s} {c:5d}")
print("\ndisapproved 样例(前8):")
for t, o, ids in samples:
    print(f"  {t} | {o} | {ids}")
