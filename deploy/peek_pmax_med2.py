# -*- coding: utf-8 -*-
"""PMax Medical Estry 诊断 v3：
C) asset_group_asset 状态（field_type 修正版）
D) REST 直读 3 个树节点 caseValue
F) Shopify 镜像库 product_type 分布（验证 'Medical Battery' 匹配量）
"""
import os
from collections import Counter

import httpx
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

CID = "7059800494"
AG = "6770847164"
NODES = ("15579051589", "15579051592", "15579051595")
TOK = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {TOK}", "developer-token": "unused",
     "login-customer-id": CID}


def gaql(query):
    r = httpx.post(
        f"https://googleads.googleapis.com/v25/customers/{CID}/googleAds:searchStream",
        headers=H, json={"query": query}, timeout=90)
    if r.status_code != 200:
        print("GAQL error:", r.status_code, r.text[:600])
        return []
    return [row for batch in r.json() for row in batch.get("results", [])]


print("=" * 20, f"C) assets of ag={AG}", "=" * 20)
rows = gaql(f"""
    SELECT asset_group_asset.field_type,
      asset_group_asset.status, asset_group_asset.source, asset.type
    FROM asset_group_asset
    WHERE asset_group.id = {AG}""")
stat = Counter()
for r in rows:
    a = r["assetGroupAsset"]
    stat[(a["fieldType"], a["status"])] += 1
    print(f"- {a['fieldType']:<22} {a['status']:<10} "
          f"src={a.get('source','?'):<22} {r.get('asset',{}).get('type','?')}")
print("分布:", {f"{k[0]}:{k[1]}": v for k, v in stat.items()}
      or "(无绑定资产!)")

print("\n" + "=" * 20, "D) 节点 caseValue (REST)", "=" * 20)
for nid in NODES:
    r = httpx.get(
        f"https://googleads.googleapis.com/v25/customers/{CID}/"
        f"assetGroupListingGroupFilters/{AG}~{nid}",
        headers=H, timeout=60)
    if r.status_code == 200:
        print(f"- node {nid}:", r.text)
    else:
        print(f"- node {nid}: HTTP {r.status_code} {r.text[:200]}")

print("\n" + "=" * 20, "F) 镜像库 product_type 分布", "=" * 20)
try:
    import pymysql
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", ""),
        port=int(os.environ.get("DB_PORT", "63698")),
        user=os.environ.get("DB_USER") or os.environ.get("DB_USERNAME", "root"),
        password=os.environ.get("DB_PASSWORD")
        or os.environ.get("DB_PASS", ""),
        database=os.environ.get("DB_NAME", "shopify_admin"),
        charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT product_type, COUNT(*) FROM products "
                "GROUP BY product_type ORDER BY 2 DESC LIMIT 15")
    for t, n in cur.fetchall():
        mark = "  <-- 树的筛选值" if t == "Medical Battery" else ""
        print(f"- {t!r}: {n}{mark}")
    cur.execute("SELECT product_type, COUNT(*) FROM products "
                "WHERE product_type LIKE '%Medical%' "
                "GROUP BY product_type ORDER BY 2 DESC")
    print("\n含 Medical 的类型:")
    for t, n in cur.fetchall():
        print(f"- {t!r}: {n}")
    conn.close()
except Exception as e:  # noqa
    print("DB 查询失败:", e)
    print("DB_* keys:", [k for k in os.environ if k.startswith("DB_")])
