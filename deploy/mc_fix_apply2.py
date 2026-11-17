# -*- coding: utf-8 -*-
"""MC 修复收尾：
B2. 死链3个用完整 resource id 重删
D2. 找库内图源表；无源则缺图8个下架 draft
E. 抽验 metafield 写入
"""
import json
import os
import sys
import urllib.parse
from collections import defaultdict

import httpx
from dotenv import load_dotenv
from sqlalchemy import text

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.core.database import get_engine  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

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

# B2 完整 id 重删
for r, _ in uniq["landing_page_error"]:
    full_id = r["id"]  # online:en:US:shopify_US_...
    q = urllib.parse.quote(full_id, safe="")
    d = httpx.delete(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MID}"
        f"/products/{q}", headers=H, timeout=30)
    print(f"B2 MC移除 {full_id[:48]}: HTTP {d.status_code}"
          + ("" if d.status_code in (200, 204) else f" {d.text[:150]}"))

# D2 图源表探查
eng = get_engine()
with eng.connect() as c:
    tabs = [r[0] for r in c.execute(text("SHOW TABLES"))]
cand = [t for t in tabs if any(k in t.lower()
                               for k in ("cs", "remote", "source", "vendor"))]
print(f"\nD2 候选表: {cand}")
img_src = None
with eng.connect() as c:
    for t in cand:
        cols = [r[0] for r in c.execute(text(
            "SELECT column_name FROM information_schema.columns "
            f"WHERE table_name='{t}' AND table_schema=DATABASE()"))]
        ic = [x for x in cols if "img" in x.lower() or "image" in x.lower()]
        if ic:
            print(f"  {t}: 图列 {ic}")
            img_src = (t, ic[0])
            break

cl = ShopifyRest(StoreService().get_client(1)).client
pids = [r["offerId"].split("_")[2]
        for r, _ in uniq["item_missing_required_attribute"]]

if img_src:
    t, col = img_src
    with eng.connect() as c:
        for pid in pids:
            row = c.execute(text(
                f"SELECT {col} FROM {t} WHERE product_id=:i OR id=:i"),
                {"i": int(pid)}).first()
            print(f"  {pid} 图源: {row[0][:90] if row and row[0] else '无'}")
    print("（有图源列，补图动作下一步脚本做）")
else:
    for pid in pids:
        cl.request("PUT", f"products/{pid}.json", json_body={
            "product": {"id": int(pid), "status": "draft"}})
        print(f"D2 缺图无源 → 已下架 draft: {pid}")

# E metafield 抽验
pid0 = uniq["guns_parts_policy_violation"][0][0]["offerId"].split("_")[2]
mf = cl.request("GET", f"products/{pid0}/metafields.json",
                params={"limit": 50})
g = [m for m in mf.get("metafields", [])
     if m["namespace"] == "google" and m["key"] == "product_category"]
print(f"\nE 抽验 {pid0} google.product_category = "
      f"{g[0]['value'] if g else '【未找到】'}")
