# -*- coding: utf-8 -*-
"""B3: 构造 online:en:US:{offerId} 重删死链；F: 24个 local_lack_inventory 免费位dis 深挖。"""
import json
import os
import urllib.parse
from collections import defaultdict

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MID = "136469408"

recs = json.load(open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json"))
seen, uniq = set(), defaultdict(list)
for r in recs:
    for i in r["issues"]:
        k = (r["offerId"], i["code"])
        if k not in seen:
            seen.add(k)
            uniq[i["code"]].append((r, i))

tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

# B3 死链重删（构造标准资源名）
for r, _ in uniq["landing_page_error"]:
    full = f"online:en:US:{r['offerId']}"
    q = urllib.parse.quote(full, safe="")
    d = httpx.delete(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MID}"
        f"/products/{q}", headers=H, timeout=30)
    ok = d.status_code in (200, 204)
    print(f"B3 {full[:52]}: HTTP {d.status_code}"
          + ("" if ok else f" {d.text[:120]}"))

# F local_stores_lack_inventory 中免费位 disapproved 的产品
dis = [(r, i) for r, i in uniq["local_stores_lack_inventory"]
       if r["ctx"].get("FREE_LISTINGS") == "disapproved"]
print(f"\nF local_lack_inventory 免费位dis {len(dis)} 个，其中前6个完整issue:")
for r, i in dis[:6]:
    codes = [x["code"] for x in r["issues"]]
    print(f"  {r['offerId'][:38]} ctx={r['ctx']} issues={codes}")
    print(f"    {r['title'][:64]}")
