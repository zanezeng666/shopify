# -*- coding: utf-8 -*-
"""抽样下载主图用于条码/CS品牌露出审查(只读)。"""
import random
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

OUT = Path("/tmp/audit_img")
OUT.mkdir(exist_ok=True)
KEYS = ["Zebra", "Motorola", "Honeywell", "TomTom", "Oral-B", "Intermec"]
random.seed(42)

params = {"limit": 250, "status": "active", "fields": "id,title,images"}
all_prods = []
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    all_prods += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,title,images"}

print(f"产品总数: {len(all_prods)}", flush=True)
picked = {}
for k in KEYS:
    cand = [p for p in all_prods if k.lower() in p["title"].lower()
            and p.get("images")]
    for p in random.sample(cand, min(3, len(cand))):
        picked[p["id"]] = (k, p)
rest = [p for p in all_prods if p["id"] not in picked and p.get("images")]
for p in random.sample(rest, 24 - len(picked)):
    picked[p["id"]] = ("rnd", p)

with httpx.Client(timeout=30, follow_redirects=True) as hc:
    for pid, (tag, p) in picked.items():
        src = p["images"][0]["src"]
        fn = OUT / f"{tag}_{pid}.jpg"
        try:
            b = hc.get(src).content
            fn.write_bytes(b)
            print(f"OK {fn.name} {len(b) // 1024}KB | {p['title'][:55]}")
        except Exception as ex:
            print(f"DL失败 {src[:70]} {str(ex)[:50]}")
print(f"下载完成: {len(list(OUT.glob('*.jpg')))} 张 -> {OUT}")
