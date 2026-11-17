# -*- coding: utf-8 -*-
"""MC 违规明细全量拉取：按 reportingContext 统计 itemLevelIssues，明细落盘。"""
import json
import os
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"
BASE = f"https://merchantapi.googleapis.com/products/v1/accounts/{MID}/products"

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

CTX_NAMES = {"FREE_LISTINGS": "免费位", "SHOPPING_ADS": "PMax/Shopping"}
issue_cnt = {}          # ctx -> Counter(code)
records = []            # 违规产品明细
total, page_token = 0, None
while True:
    url = f"{BASE}?pageSize=250" + (f"&pageToken={page_token}" if page_token
                                    else "")
    r = httpx.get(url, headers=H, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"API {r.status_code}: {r.text[:300]}")
    j = r.json()
    for p in j.get("products", []):
        total += 1
        ps = p.get("productStatus") or {}
        # 目标 context 的国家级状态
        ctx_st = {}
        for d in ps.get("destinationStatuses", []):
            ctx = d.get("reportingContext", "?")
            lv = d.get("disapprovedCountries") and "disapproved" or (
                d.get("pendingCountries") and "pending" or "approved")
            ctx_st[ctx] = lv
        issues = [i for i in ps.get("itemLevelIssues", [])
                  if i.get("severity") != "NOT_IMPACTED"]
        if not issues:
            continue
        attr = p.get("productAttributes") or {}
        rec = {"offerId": p.get("offerId", ""),
               "id": p.get("id", "").split("/")[-1],
               "title": (attr.get("title") or "")[:70],
               "link": attr.get("link") or "",
               "image": bool(attr.get("imageLink")),
               "ctx": ctx_st,
               "issues": [{"code": i.get("code"),
                           "desc": (i.get("description") or "")[:90],
                           "detail": (i.get("detail") or "")[:140],
                           "docs": i.get("documentation") or ""}
                          for i in issues]}
        records.append(rec)
        for i in issues:
            for ctx in (i.get("applicableReportingContexts") or ["?"]):
                issue_cnt.setdefault(ctx, Counter())[i.get("code")] += 1
    page_token = j.get("nextPageToken")
    if not page_token:
        break

print(f"=== MC {MID} 总商品 {total}，带 issue 的 {len(records)} ===\n")
for ctx, cnt in sorted(issue_cnt.items()):
    name = CTX_NAMES.get(ctx, ctx)
    print(f"-- {name} ({ctx}) --")
    for code, c in cnt.most_common(15):
        print(f"  {code:44s} {c:4d}")

with open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json",
          "w") as f:
    json.dump(records, f, ensure_ascii=False, indent=1)
print(f"\n明细已落 deploy/mc_issues_20261116.json")
