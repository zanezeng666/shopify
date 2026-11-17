# -*- coding: utf-8 -*-
"""查数据源详情 + 死链清单的 ds 分布，评估整删旧源方案。"""
import json
import os
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
MC = "136469408"

at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
HD = {"Authorization": f"Bearer {at}"}

print("=== 数据源列表 ===")
r = httpx.get(
    f"https://merchantapi.googleapis.com/datasources/v1/accounts/{MC}"
    f"/dataSources", params={"pageSize": 50}, headers=HD, timeout=60)
print(f"HTTP {r.status_code}")
for ds in r.json().get("dataSources", []):
    name = ds.get("name", "")
    print(f"\n· {name}")
    print(f"  displayName={ds.get('displayName')!r}")
    for k in ("primaryDataSource", "supplementalFeed", "localInventorySource",
              "channel", "input", "fileInput"):
        if k in ds:
            print(f"  {k}: {str(ds[k])[:90]}")

print("\n=== 死链清单 ds 分布 ===")
d = json.load(open("/home/jason/shopify-admin/deploy/mc_purge_state2.json"))
cnt = Counter(p["ds"] for p in d["dead_olddsr"])
print(dict(cnt))
nonold = [p for p in d["dead_olddsr"] if p["ds"] != "10604168290"]
for p in nonold[:6]:
    print(f"  非旧源死链: ds={p['ds']} offer={p['offer'][:40]} "
          f"archived={p['archived']} types={p['types']}")
