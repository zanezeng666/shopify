# -*- coding: utf-8 -*-
"""巨组详情（与试点/统计完全同口径）：主品链接+品牌构成+容量谱。"""
import os
import sys
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

# ---- 源库分组（同试点口径）----
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product")
groups = defaultdict(list)
for cs_id, pn, fm, cap in cc.fetchall():
    if pn and fm:
        groups[(pn, fm)].append((cs_id, cap))
cs.close()
csid2cap, gid_of, gkey = {}, {}, {}
for gi, (k, mem) in enumerate(groups.items()):
    gkey[gi] = k
    for cs_id, cap in mem:
        csid2cap[cs_id] = cap
        gid_of[cs_id] = gi

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,title,handle,status,variants", "status": "active"}
live = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    live += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
           if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

agg = defaultdict(list)
for p in live:
    v = (p["variants"] or [{}])[0]
    cs_id = (v.get("sku") or "").split("_")[0]
    gi = gid_of.get(cs_id)
    if gi is None:
        continue
    agg[gi].append({
        "pid": p["id"], "handle": p["handle"], "title": p["title"],
        "cap": csid2cap.get(cs_id), "cs_id": cs_id,
        "sku": v.get("sku"), "price": v.get("price"),
    })

big = []
for gi, mem in agg.items():
    caps = {m["cap"] for m in mem if m["cap"]}
    if len(mem) > 8 and len(caps) >= 2 and all(m["cap"] for m in mem):
        big.append(mem)
print(f"巨组数: {len(big)} | 合计 {sum(len(m) for m in big)} 页\n")
for i, mem in enumerate(sorted(big, key=lambda m: -len(m)), 1):
    main = max(mem, key=lambda x: len(x["title"]))
    caps = sorted({m["cap"] for m in mem})
    br = defaultdict(int)
    for m in mem:
        b = (m["sku"] or "?").split("_")[1] if m.get("sku") and "_" in m["sku"] else "?"
        br[b] += 1
    brs = ", ".join(f"{b}×{n}" for b, n in sorted(br.items(), key=lambda y: -y[1]))
    print(f"【组{i}】{len(mem)} 页 | 容量 {len(caps)} 种")
    print(f"  主品: {main['title'][:100]}")
    print(f"  链接: https://estrybattery.com/products/{main['handle']}")
    print(f"  容量: {caps}")
    print(f"  品牌: {brs}\n")
