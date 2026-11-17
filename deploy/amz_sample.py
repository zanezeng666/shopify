# -*- coding: utf-8 -*-
"""随机抽 20 个在售变体，生成亚马逊比价任务清单 TSV。"""
import csv
import random
import re
import time

import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

random.seed(20261110)

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "status": "active",
          "fields": "id,handle,title,product_type,variants"}
allp, page = [], 0
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    batch = r.json()["products"]
    allp += batch
    page += 1
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print(f"活跃产品: {len(allp)} 个 ({page} 页)")

cands = []
for p in allp:
    for v in p["variants"]:
        try:
            price = float(v.get("price") or 0)
        except Exception:
            price = 0
        sku = v.get("sku") or ""
        if price > 0 and sku.startswith("CS-"):
            cands.append({
                "vid": v["id"], "sku": sku, "price": price,
                "title": p["title"], "ptype": p.get("product_type") or "",
                "handle": p["handle"]})
print(f"候选变体: {len(cands)}")

def search_key(title):
    """从标题提炼亚马逊搜索词：'... for <设备>' 优先，回退前 8 词。"""
    t = re.sub(r"[^\w\s+.-]", " ", title)
    m = re.search(r"\bfor\s+(.+)", t, re.I)
    if m:
        words = m.group(1).split()[:6]
        return " ".join(words)
    return " ".join(t.split()[:8])

rows = random.sample(cands, 20)
out = "/home/jason/shopify-admin/deploy/amz_sample.tsv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter="\t")
    w.writerow(["vid", "sku", "our_price", "search_key", "ptype", "title"])
    for r in rows:
        w.writerow([r["vid"], r["sku"], r["price"], search_key(r["title"]),
                    r["ptype"], r["title"][:90]])
print(f"抽样 20 -> {out}")
for r in rows[:5]:
    print(" 样例:", r["sku"], r["price"], "|", search_key(r["title"]))
