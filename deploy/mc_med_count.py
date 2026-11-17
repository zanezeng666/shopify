# -*- coding: utf-8 -*-
"""验证树筛选条件与MC商品数据的匹配：
SHOPPING_ADS approved 商品的 product_type level1 分布"""
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

type_all, type_ok = Counter(), Counter()
med_ok = med_total = 0
page_token, total = None, 0
while True:
    url = f"{BASE}?pageSize=250" + (f"&pageToken={page_token}" if page_token else "")
    r = httpx.get(url, headers=H, timeout=60)
    if r.status_code != 200:
        raise SystemExit(f"API {r.status_code}: {r.text[:200]}")
    j = r.json()
    for p in j.get("products", []):
        total += 1
        pa = p.get("productAttributes") or {}
        types = pa.get("productTypes") or ([pa["productType"]] if pa.get("productType") else [])
        lv1 = (types[0] if types else "(无type)").strip().lower()
        ps = p.get("productStatus") or {}
        ok = False
        for d in ps.get("destinationStatuses", []):
            if d.get("reportingContext") == "SHOPPING_ADS":
                ok = "US" in (d.get("approvedCountries") or [])
                break
        type_all[lv1] += 1
        if ok:
            type_ok[lv1] += 1
        if "medical battery" in lv1:
            med_total += 1
            med_ok += ok
    page_token = j.get("nextPageToken")
    if not page_token:
        break

print(f"MC 在线商品总数: {total}")
print(f"\n'medical battery' 类: 总数 {med_total} | SHOPPING_ADS批准 {med_ok}")
print("\nlevel1 分类分布 Top15 (总数 / 批准):")
for t, c in type_all.most_common(15):
    print(f"  {t[:40]:42s} {c:5d} / {type_ok.get(t, 0)}")
