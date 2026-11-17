# -*- coding: utf-8 -*-
"""变体合并试点：5 组全流程。
规则: (part_no, fit_model) 一致 + 容量>=2 + 线上>=2 active -> Capacity 变体。
主品: 组内 title 最长页。同容量多页取最低价代表。
顺序: 读组 -> 修主品 option 名/值 -> 建无sku变体 -> 删非主品页+301+追图
      -> 变体补 sku。
"""
import os
import sys
import time
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

BASE = "https://estrybattery.com"
PILOT_N = 5

# ---- 1) 源库分组 ----
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

csid2cap, gid_of = {}, {}
for gi, (key, mem) in enumerate(groups.items()):
    for cs_id, cap in mem:
        csid2cap[cs_id] = cap
        gid_of[cs_id] = gi

cl = ShopifyRest(StoreService().get_client(1)).client

# ---- 2) 线上 active 产品 ----
params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,title,handle,status,variants,images", "status": "active"}
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
        "cap": csid2cap.get(cs_id), "cs_id": cs_id, "sku": v.get("sku"),
        "price": v.get("price"), "grams": v.get("grams"),
        "img": (p.get("images") or [{}])[0].get("src"),
    })

mergeable = []
for gi, members in agg.items():
    caps = {m["cap"] for m in members if m["cap"]}
    if len(members) >= 2 and len(caps) >= 2 and all(m["cap"] for m in members):
        mergeable.append(members)
mergeable.sort(key=lambda m: -len({x["cap"] for x in m}))
pilot = mergeable[:PILOT_N]
print(f"可合并 {len(mergeable)} 组，试点 {len(pilot)} 组\n")

for gi, members in enumerate(pilot):
    print(f"=== 试点组 {gi+1} ===")
    main = max(members, key=lambda x: len(x["title"] or ""))
    others = [m for m in members if m["pid"] != main["pid"]]
    by_cap = defaultdict(list)
    for m in members:
        by_cap[m["cap"]].append(m)

    # a) 主品 option 名=Capacity + 现有变体 option1=自身容量
    mp = cl.request("GET", f"products/{main['pid']}.json").get("product", {})
    if mp["options"][0].get("name") != "Capacity":
        cl.request("PUT", f"products/{main['pid']}.json", json_body={"product": {
            "id": main["pid"], "options": [{"name": "Capacity"}]}})
        print("  option 名 -> Capacity")
    mv = mp["variants"][0]
    if mv.get("option1") != main["cap"]:
        cl.request("PUT", f"variants/{mv['id']}.json", json_body={"variant": {
            "id": mv["id"], "option1": main["cap"]}})
        print(f"  主品变体 {mv.get('option1')!r} -> {main['cap']!r}")

    # b) 其他容量建变体（无 sku，避免冲突；幂等：已存在则纳入补 sku）
    fresh = cl.request("GET", f"products/{main['pid']}.json",
                       params={"fields": "variants"}).get("product", {})
    existing = {v["option1"]: v for v in fresh["variants"]}
    todo = []
    for cap, ms in sorted(by_cap.items()):
        if cap == main["cap"]:
            continue
        rep = min(ms, key=lambda x: float(x["price"] or 0))
        if cap in existing:
            todo.append((rep, existing[cap]["id"]))
            continue
        try:
            nv = cl.request("POST", f"products/{main['pid']}/variants.json",
                            json_body={"variant": {
                                "option1": cap, "price": rep["price"],
                                "grams": rep["grams"] or 0,
                                "requires_shipping": True}})
            vid = nv.get("variant", {}).get("id")
        except Exception as e:
            print(f"  ! 建变体失败 {cap!r}: {e}")
            continue
        todo.append((rep, vid))
        print(f"  + 变体 {cap!r} ${rep['price']}")

    # c) 删非主品页 + 301（追图砍掉：Shopify CDN 图源复用会 422，主品自有图足够）
    for m in others:
        try:
            cl.request("DELETE", f"products/{m['pid']}.json")
        except Exception:
            print(f"  ! 删页可能已删: {m['handle'][:40]}")
        try:
            cl.request("POST", "redirects.json", json_body={"redirect": {
                "path": f"/products/{m['handle']}",
                "target": f"/products/{main['handle']}"}})
        except Exception:
            pass
        print(f"  - 删页+301: {m['handle'][:55]}")

    # d) 变体补 sku
    for rep, vid in todo:
        if vid:
            cl.request("PUT", f"variants/{vid}.json", json_body={"variant": {
                "id": vid, "sku": rep["sku"]}})
    print(f"  => {BASE}/products/{main['handle']}\n")
    time.sleep(1)
