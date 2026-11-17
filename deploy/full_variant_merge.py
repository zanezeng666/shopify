# -*- coding: utf-8 -*-
"""全量变体合并：272 组。规则与增强同试点修复版，含快照/断点/库存/排序。"""
import json
import os
import re
import sys
import time
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

SNAP = "/home/jason/shopify-admin/deploy/merge_snapshot.json"
STATE = "/home/jason/shopify-admin/deploy/merge_state.json"
DRY = "--dry" in sys.argv
LIM = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0

rest = ShopifyRest(StoreService().get_client(1))
cl = rest.client


def req(method, path, **kw):
    time.sleep(0.35)
    r = getattr(cl._client, method.lower())(path, auth=cl._auth, **kw)
    r.raise_for_status()
    return r.json() if r.content and method != "DELETE" else {}


def cap_num(s):
    m = re.search(r"\d+(\.\d+)?", str(s))
    return float(m.group(0)) if m else -1.0


# ---- 1) 快照: 源库分组 + 料号表 + 线上页 ----
if os.path.exists(SNAP):
    snap = json.load(open(SNAP, encoding="utf-8"))
    print(f"读快照 {len(snap['targets'])} 组")
else:
    cs = pymysql.connect(
        host=os.environ["CS_DB_HOST"],
        port=int(os.environ.get("CS_DB_PORT", 3306)),
        user=os.environ["CS_DB_USER"],
        password=os.environ["CS_DB_PASSWORD"],
        database=os.environ["CS_DB_NAME"], charset="utf8mb4")
    cc = cs.cursor()
    cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product")
    groups = defaultdict(list)
    tok = defaultdict(lambda: {"pn": set(), "fm": set()})
    for cs_id, pn, fm, cap in cc.fetchall():
        if pn and fm:
            groups[(pn, fm)].append((cs_id, cap))
        row = tok[cs_id]
        for t in re.split(r"[,;/|]", pn or ""):
            if t.strip():
                row["pn"].add(t.strip())
        for t in re.split(r"[,;/|]", fm or ""):
            if t.strip():
                row["fm"].add(t.strip())
    cs.close()
    csid2cap, gid_of, gkey = {}, {}, {}
    for gi, (k, mem) in enumerate(groups.items()):
        gkey[str(gi)] = list(k)
        for cs_id, cap in mem:
            csid2cap[cs_id] = cap
            gid_of[cs_id] = gi
    params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
              "fields": "id,title,handle,variants", "status": "active"}
    live = []
    while True:
        r = cl._client.get("products.json", params=params, auth=cl._auth)
        r.raise_for_status()
        live += r.json()["products"]
        link = r.headers.get("Link", "")
        nxt = [x.split(";")[0].strip("<>")
               for x in link.split(",") if 'rel="next"' in x]
        if not nxt:
            break
        params = {"limit": 250,
                  "page_info": nxt[0].split("page_info=")[-1]}
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
            "grams": v.get("grams") or 0})
    targets = []
    for gi, mem in agg.items():
        caps = {m["cap"] for m in mem if m["cap"]}
        if len(mem) >= 2 and len(caps) >= 2 and all(m["cap"] for m in mem):
            targets.append(mem)
    snap = {
        "gkey": gkey,
        "tok": {k: {"pn": sorted(v["pn"]), "fm": sorted(v["fm"])}
                for k, v in tok.items()},
        "targets": targets}
    json.dump(snap, open(SNAP, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"建快照 {len(targets)} 组")

targets = snap["targets"]
tok = snap["tok"]
if LIM:
    targets = targets[:LIM]

state = {"done": [], "errors": {}}
if os.path.exists(STATE):
    state = json.load(open(STATE, encoding="utf-8"))
done = set(state["done"])

# ---- 2) 库存表 ----
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"],
    port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()


def inv_sum(csid):
    cc.execute("SELECT COALESCE(SUM(quantity),0) FROM cs_inventory "
               "WHERE cs_id=%s", (csid,))
    return int(cc.fetchone()[0])


locs = req("GET", "locations.json")["locations"]
LOC = next(l["id"] for l in locs if "Cameron" in l["name"])

print(f"目标 {len(targets)} 组 | 已完成 {len(done)} | DRY={DRY}")
n_del = n_var = 0
for gi, mem in enumerate(targets):
    key = json.dumps([m["pid"] for m in sorted(mem, key=lambda x: x["pid"])])
    if key in done:
        continue
    main = max(mem, key=lambda x: (len(x["title"]), -x["pid"]))
    others = [m for m in mem if m["pid"] != main["pid"]]
    by_cap = {}
    for m in sorted(mem, key=lambda x: float(x["price"] or 0)):
        if float(m["price"] or 0) > 0:
            by_cap.setdefault(m["cap"], m)
    caps_want = set(by_cap)  # 0 价容量(含 0 价主品容量)不入
    if not caps_want:
        print("  跳过: 组内全 0 价（数据问题，保持原状）")
        state["done"].append(key)
        json.dump(state, open(STATE, "w", encoding="utf-8"),
                  ensure_ascii=False)
        continue
    print(f"\n[{gi + 1}/{len(targets)}] {len(mem)}页 -> {main['handle'][:50]}"
          f" 容量{sorted(caps_want)} 删{len(others)}")
    if DRY:
        n_del += len(others)
        continue
    try:
        # a) option 名 + 首变体 option1
        mp = req("GET", f"products/{main['pid']}.json",
                 params={"fields": "id,title,handle,options,variants"}
                ).get("product", {})
        if not mp:
            print("  主品缺失(已处理?) 跳过")
            state["done"].append(key)
            continue
        if (mp.get("options") or [{}])[0].get("name") != "Capacity":
            req("PUT", f"products/{main['pid']}.json",
                json={"product": {"id": main["pid"],
                                  "options": [{"name": "Capacity"}]}})
        mvs = mp.get("variants") or []
        if mvs and mvs[0].get("option1") != main["cap"]:
            req("PUT", f"variants/{mvs[0]['id']}.json",
                json={"variant": {"id": mvs[0]["id"],
                                  "option1": main["cap"]}})
        # b) 幽灵变体清理 + 建缺失变体
        exist = {}
        for v in mvs:
            exist[v["option1"]] = v
        for o1, v in list(exist.items()):
            if o1 not in caps_want and len(exist) > 1:
                req("DELETE", f"variants/{v['id']}.json")
                del exist[o1]
                print(f"  - 幽灵变体 {o1}")
        final = {}
        for cap in caps_want:
            rep = by_cap.get(cap) or main
            if cap in exist:
                v = exist[cap]
                final[cap] = {"vid": v["id"], "iid": v.get("inventory_item_id"),
                              "sku": v.get("sku")}
                if abs(float(v.get("price") or 0) - float(rep["price"])) > .01:
                    req("PUT", f"variants/{v['id']}.json",
                        json={"variant": {"id": v["id"],
                                          "price": rep["price"]}})
                    print(f"  ~ 价 {cap} -> {rep['price']}")
                if not v.get("sku") and rep.get("sku"):
                    req("PUT", f"variants/{v['id']}.json",
                        json={"variant": {"id": v["id"], "sku": rep["sku"]}})
                    final[cap]["sku"] = rep["sku"]
                    print(f"  ~ sku {cap} <- {rep['sku'][:25]}")
            else:
                nv = req("POST", f"products/{main['pid']}/variants.json",
                         json={"variant": {
                             "option1": cap, "price": rep["price"],
                             "grams": rep["grams"] or 0,
                             "requires_shipping": True}})["variant"]
                req("PUT", f"variants/{nv['id']}.json",
                    json={"variant": {"id": nv["id"], "sku": rep["sku"]}})
                final[cap] = {"vid": nv["id"],
                              "iid": nv.get("inventory_item_id"),
                              "sku": rep["sku"]}
                n_var += 1
                print(f"  + 变体 {cap} ${rep['price']}")
        # c) 库存直推
        for cap, f in final.items():
            csid = (f.get("sku") or "").split("_")[0]
            if f.get("iid") and csid:
                rest.set_inventory_level(f["iid"], LOC, inv_sum(csid))
        # d) 容量降序
        order = sorted(final, key=cap_num, reverse=True)
        req("PUT", f"products/{main['pid']}.json",
            json={"product": {"id": main["pid"], "variants": [
                {"id": final[c]["vid"], "position": i + 1}
                for i, c in enumerate(order)]}})
        # e) 删页 + 301
        for m in others:
            try:
                req("DELETE", f"products/{m['pid']}.json")
            except Exception:
                print(f"  ! 删页失败(已删?) {m['handle'][:40]}")
            try:
                req("POST", "redirects.json", json={"redirect": {
                    "path": f"/products/{m['handle']}",
                    "target": f"/products/{main['handle']}"}})
            except Exception:
                pass
            n_del += 1
        # f) 标题增强: 被删页料号并入
        tl = main["title"].lower()
        adds, seen = [], set()
        for m in others:
            t = tok.get(m["cs_id"]) or {"pn": [], "fm": []}
            for grp, allow_space in (("pn", True), ("fm", False)):
                for x in t[grp]:
                    if len(x) < 5 or not re.search(r"\d", x):
                        continue
                    if not allow_space and " " in x:
                        continue
                    if x.lower() in tl or x.lower() in seen:
                        continue
                    seen.add(x.lower())
                    adds.append((0 if grp == "pn" else 1, x))
        adds.sort()
        words = main["title"].split() + [x for _, x in adds]
        while len(" ".join(words)) > 255 and len(words) > len(main["title"].split()):
            words.pop()
        nt = " ".join(words)
        if nt != main["title"]:
            req("PUT", f"products/{main['pid']}.json",
                json={"product": {"id": main["pid"], "title": nt}})
            print(f"  T 标题+{len(words) - len(main['title'].split())} token")
        state["done"].append(key)
    except Exception as e:
        state["errors"][str(main["pid"])] = str(e)[:200]
        print(f"  !! 组失败: {e}")
    json.dump(state, open(STATE, "w", encoding="utf-8"),
              ensure_ascii=False)
cs.close()
print(f"\n完成: 删页 {n_del} 新变体 {n_var} 错误 {len(state['errors'])}")
if state["errors"]:
    for k, v in list(state["errors"].items())[:10]:
        print(f"  err {k}: {v}")
