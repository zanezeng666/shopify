# -*- coding: utf-8 -*-
"""全店主图条码扫描: 下载主图 -> zxing 解码 EAN/UPC -> 风险清单(只读)。

Google 图像识别会扫主图条码并与提交 GTIN 比对(MPN模式下提交的是SKU,
主图若露出 EAN 条码存在不匹配风险)。此脚本量化该风险。
"""
import io
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
import zxingcpp
from PIL import Image

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

# ---- 1) 拉全店 active 产品主图 URL ----
params = {"limit": 250, "status": "active", "fields": "id,title,images"}
prods = []
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    for p in r.json()["products"]:
        if p.get("images"):
            prods.append((p["id"], p["title"], p["images"][0]["src"]))
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,title,images"}
print(f"产品: {len(prods)}", flush=True)

OUT = Path("/home/jason/shopify-admin/deploy/barcode_scan_result.jsonl")
if OUT.exists():
    OUT.unlink()

HC = httpx.Client(timeout=20, follow_redirects=True,
                  limits=httpx.Limits(max_connections=10))


def scan(item):
    pid, title, src = item
    try:
        b = HC.get(src).content
        img = Image.open(io.BytesIO(b)).convert("RGB")
        if img.width > 1200:
            img = img.resize((1200, int(img.height * 1200 / img.width)))
        res = zxingcpp.read_barcodes(img)
        return pid, title, [(x.text, x.format.name) for x in res]
    except Exception as ex:
        return pid, title, [("__ERR__", str(ex)[:60])]


found = err = 0
with ThreadPoolExecutor(10) as tp:
    futs = [tp.submit(scan, it) for it in prods]
    for i, f in enumerate(as_completed(futs), 1):
        pid, title, codes = f.result()
        if codes and codes[0][0] == "__ERR__":
            err += 1
        elif codes:
            found += 1
            with open(OUT, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"pid": pid, "title": title[:80],
                                     "codes": codes}) + "\n")
        if i % 500 == 0:
            print(f"进度 {i}/{len(prods)} 检出条码={found} 错误={err}",
                  flush=True)

print(f"扫描完成: 总数={len(prods)} 检出条码={found} 错误={err}", flush=True)
print(f"结果: {OUT}", flush=True)
