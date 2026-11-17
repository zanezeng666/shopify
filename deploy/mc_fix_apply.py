# -*- coding: utf-8 -*-
"""MC 违规修复实施：
A. 烟草1个 -> Shopify 下架 draft
B. 死链3个 -> Merchant API 删除残留 offer
C. 枪械6+濒危2+local_req20 -> 写 google.product_category metafield
D. 缺图8 -> 探查库表图源列（先摸清再补/下架）
"""
import json
import os
import sys
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

def pid_of(r):
    p = r["offerId"].split("_")
    return p[2], (p[3] if len(p) > 3 else "")

cl = ShopifyRest(StoreService().get_client(1)).client

# D 先探表结构（找图源列）
eng = get_engine()
with eng.connect() as c:
    cols = [r[0] for r in c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='products' AND table_schema=DATABASE()"))]
img_cols = [x for x in cols if any(k in x.lower()
                                   for k in ("img", "image", "pic", "photo"))]
print(f"products 表图源候选列: {img_cols}")

# A 烟草下架
for r, _ in uniq["tobacco_policy_violation"]:
    pid, _ = pid_of(r)
    cl.request("PUT", f"products/{pid}.json", json_body={
        "product": {"id": int(pid), "status": "draft"}})
    print(f"A 烟草已下架 draft: {pid} {r['title'][:50]}")

# B 死链 MC 移除
tok = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_MC_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}
for r, _ in uniq["landing_page_error"]:
    oid = r["offerId"]
    d = httpx.delete(
        f"https://merchantapi.googleapis.com/products/v1/accounts/{MID}"
        f"/products/{oid}", headers=H, timeout=30)
    print(f"B MC移除 {oid[:40]}: HTTP {d.status_code}"
          + ("" if d.status_code == 200 else f" {d.text[:120]}"))

# C category metafield（枪6+濒危2+local_req20）
GPC = {"namespace": "google", "key": "product_category",
       "type": "single_line_text_field", "value": "Hardware > Batteries"}
targets = (uniq["guns_parts_policy_violation"]
           + uniq["endangered_species_policy_violation"]
           + uniq["local_requirements_policy_violation"])
ok = fail = 0
for r, _ in targets:
    pid, _ = pid_of(r)
    try:
        cl.request("POST", f"products/{pid}/metafields.json",
                   json_body={"metafield": GPC})
        ok += 1
    except Exception as e:  # noqa
        fail += 1
        print(f"  C 失败 {pid}: {e}")
print(f"C google.product_category 写入 {len(targets)} 个: ok={ok} fail={fail}")

# D 缺图8个：列出库内图源值（下一步决策）
if img_cols:
    col = img_cols[0]
    with eng.connect() as c:
        for r, _ in uniq["item_missing_required_attribute"]:
            pid, _ = pid_of(r)
            row = c.execute(text(
                f"SELECT {col} FROM products WHERE id=:i"),
                {"i": int(pid)}).first()
            v = (row[0][:80] if row and row[0] else "无")
            print(f"D 缺图 {pid} {col}={v}")
