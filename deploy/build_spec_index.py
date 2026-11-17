# -*- coding: utf-8 -*-
"""Estry 规格索引构建: 镜像库 active 变体 × CS 规格库 JOIN → 紧凑 JSON 分片 → theme assets.

产出 (theme 190031036660):
  assets/spec-idx-manifest.json   分片清单+预计算分面值
  assets/spec-idx-0.json ... N    条目分片 (每 csid 一条, 含 handle/规格/兼容型号)
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python build_spec_index.py
幂等: 先删旧 spec-idx-* 再传新; 重跑即全量刷新.
"""
import json
import os
import re
import sys
import time
from decimal import Decimal

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
PREFIX = "spec-idx"
c = ShopifyRest(StoreService().get_client(1)).client

# ---------- 1. 拉数据 ----------
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
sh = pymysql.connect(
    host=os.environ.get("SHOPIFY_DB_HOST", os.environ["CS_DB_HOST"]),
    port=int(os.environ.get("SHOPIFY_DB_PORT", os.environ.get("CS_DB_PORT", 3306))),
    user=os.environ.get("SHOPIFY_DB_USER", os.environ["CS_DB_USER"]),
    password=os.environ.get("SHOPIFY_DB_PASSWORD", os.environ["CS_DB_PASSWORD"]),
    database=os.environ["SHOPIFY_DB_NAME"], charset="utf8mb4")

cur = sh.cursor()
cur.execute(
    "SELECT v.sku, v.price, p.handle, p.title FROM product_variants v "
    "JOIN products p ON v.product_id=p.id "
    "WHERE p.status='active' AND v.sku LIKE 'CS-%'")
rows = cur.fetchall()
sh.close()
print(f"[1] active CS 变体: {len(rows)}")

cur = cs.cursor()
cur.execute(
    "SELECT cs_id,category,brand,part_no,fit_model,dimension,battery_type,"
    "capacity,net_weight_g,voltage,wh_value FROM cs_product")
spec = {}
for r in cur.fetchall():
    spec[r[0]] = r
cs.close()
print(f"[2] cs_product 规格: {len(spec)}")

# ---------- 2. 聚合 (每 csid 一条, price 取 min) ----------
NUM_RE = re.compile(r"[\d.]+")
agg: dict = {}
miss_spec = 0
no_handle = 0
for sku, price, handle, title in rows:
    parts = (sku or "").split("_")
    csid = parts[0]
    if not csid.startswith("CS-"):
        continue
    if not handle:
        no_handle += 1
        continue
    e = agg.get(csid)
    if e is None:
        agg[csid] = {"handle": handle, "title": title or "", "price": price}
    elif price is not None and (e["price"] is None or price < e["price"]):
        e["price"] = price


def split_list(s, limit):
    if not s:
        return []
    out, seen = [], set()
    for x in re.split(r"[,;/]", str(s)):
        x = x.strip()
        if x and x.lower() not in seen:
            seen.add(x.lower())
            out.append(x)
        if len(out) >= limit:
            break
    return out


def wh_of(volt, cap, whv):
    if whv and Decimal(whv) > 0:
        return round(float(whv), 1)
    vm = NUM_RE.search(volt or "")
    cm = NUM_RE.search(cap or "")
    if vm and cm:
        try:
            return round(float(vm.group()) * float(cm.group()) / 1000, 1)
        except (ValueError, ZeroDivisionError):
            return None
    return None


audit = {"total": 0}
items = []
for csid, e in sorted(agg.items(), key=lambda kv: (kv[1]["title"], kv[0])):
    s = spec.get(csid)
    if not s:
        miss_spec += 1
        continue
    (_, cat, br, pn, fm, dim, bt, cap, wg, volt, whv) = s
    dim = re.sub(r"\s+", " ", (dim or "")).strip()
    t = (e["title"] or "").strip()
    if t.lower().startswith("battery for "):
        t = t[12:]
    item = {
        "h": e["handle"], "m": csid, "t": t,
        "c": cat or "", "b": br or "", "ch": bt or "",
        "v": volt or "", "cap": cap or "", "wh": wh_of(volt, cap, whv),
        "d": dim, "w": wg if wg else None,
        "fm": split_list(fm, 8), "pn": split_list(pn, 4),
        "p": float(e["price"]) if e["price"] is not None else None,
    }
    items.append(item)
    audit["total"] += 1
    for k, ok in (("c", cat), ("b", br), ("ch", bt), ("v", volt),
                  ("cap", cap), ("d", dim), ("w", wg), ("pn", pn), ("fm", fm)):
        if not ok:
            audit[k] = audit.get(k, 0) + 1

# ---------- 3. 分面预计算 ----------
def facet_count(key):
    d: dict = {}
    for it in items:
        val = it[key]
        if val:
            d[val] = d.get(val, 0) + 1
    return d


fc = facet_count("c")
fb = facet_count("b")
fh = facet_count("ch")
fv = facet_count("v")


def volt_sort(x):
    m = NUM_RE.search(x)
    return float(m.group()) if m else 0.0


facets = {
    "category": sorted(fc.items(), key=lambda kv: -kv[1]),
    "brand": sorted(fb.items(), key=lambda kv: -kv[1])[:80],
    "chemistry": sorted(fh.items(), key=lambda kv: -kv[1]),
    "voltage": sorted(fv.items(), key=lambda kv: volt_sort(kv[0])),
    "capRange": [["Under 1000mAh", 0, 1000], ["1000-1999mAh", 1000, 2000],
                 ["2000-2999mAh", 2000, 3000], ["3000-4999mAh", 3000, 5000],
                 ["5000mAh & above", 5000, 999999]],
}

# ---------- 4. 分片 + manifest ----------
NSHARD = 3
shard_size = (len(items) + NSHARD - 1) // NSHARD
shards = []
for i in range(NSHARD):
    chunk = items[i * shard_size:(i + 1) * shard_size]
    if not chunk:
        break
    shards.append((f"{PREFIX}-{i}.json", json.dumps(
        chunk, ensure_ascii=False, separators=(",", ":"))))

manifest = {
    "built": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "count": len(items),
    "shards": [s[0] for s in shards],
    "facets": facets,
}
man_json = json.dumps(manifest, ensure_ascii=False, separators=(",", ":"))
total_kb = sum(len(v) for _, v in shards) / 1024
print(f"[3] 条目={len(items)} 跳过(无规格)={miss_spec} 无handle={no_handle} "
      f"分片={len(shards)} 总大小={total_kb:.0f}KB manifest={len(man_json)/1024:.0f}KB")
print("[4] 字段缺失统计:", {k: v for k, v in sorted(audit.items()) if k != "total"})

# ---------- 5. 清旧 + 上传 ----------
cur_keys = c.request("GET", f"themes/{TID}/assets.json")["assets"]
old = [a["key"] for a in cur_keys
       if a["key"].startswith(f"assets/{PREFIX}-")]
for k in old:
    c.request("DELETE", f"themes/{TID}/assets.json", params={"asset[key]": k})
    time.sleep(0.6)
if old:
    print(f"[5] 清除旧分片: {len(old)}")

for key, val in shards + [(f"{PREFIX}-manifest.json", man_json)]:
    c.request("PUT", f"themes/{TID}/assets.json",
              json_body={"asset": {"key": f"assets/{key}", "value": val}})
    time.sleep(0.6)
print(f"[6] 上传 {len(shards)+1} 个 asset 完成")

# ---------- 6. 复核 ----------
rb = json.loads(c.request(
    "GET", f"themes/{TID}/assets.json",
    params={"asset[key]": f"assets/{PREFIX}-manifest.json"})["asset"]["value"])
assert rb["count"] == len(items), "manifest count mismatch"
print(f"[7] manifest 读回 OK: count={rb['count']} built={rb['built']}")

import urllib.request  # noqa: E402

home = urllib.request.Request(
    "https://www.estrybattery.com/", headers={"User-Agent": "estry-deploy"})
html = urllib.request.urlopen(home, timeout=30).read().decode("utf-8", "ignore")
mv = re.search(r"cdn/shop/t/(\d+)/", html)
tv = mv.group(1) if mv else str(TID)
print(f"[7.5] CDN theme version: t/{tv}")
for key in rb["shards"] + [f"{PREFIX}-manifest.json"]:
    url = f"https://www.estrybattery.com/cdn/shop/t/{tv}/assets/{key}"
    req = urllib.request.Request(url, headers={"User-Agent": "estry-deploy"})
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        assert r.status == 200 and len(body) > 100, f"CDN fail {key}"
        print(f"[8] CDN {key}: HTTP {r.status} {len(body)/1024:.0f}KB")

print("BUILD-SPEC-INDEX-DONE (更新SOP: 商品/规格变更后重跑本脚本即全量刷新)")
