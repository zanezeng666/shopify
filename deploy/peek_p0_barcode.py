# -*- coding: utf-8 -*-
"""P0-2a 条码路线现状确认：
- 全店 vendor 分布（品牌一致性）
- 全店商品/变体 barcode 统计（对比 2026-11-12 的 13,533 非空基线）
- barcode 长度分布（13=EAN/Cameron Sino, 12=UPC）
- 与商品状态(active/draft/archived)交叉
"""
import time
from collections import Counter

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
from shopify_admin.services.stores.service import StoreService  # noqa

client = StoreService().get_client(1)

vendor = Counter()
prod_status = Counter()
len_dist = Counter()
status_barcode = Counter()
total_v = with_bc = 0
page = 1
since = 0
while True:
    batch = client.request("GET", "products.json", params={
        "limit": 250, "since_id": since}).get("products", [])
    if not batch:
        break
    for p in batch:
        vendor[p.get("vendor") or "(空)"] += 1
        st = p.get("status") or "?"
        prod_status[st] += 1
        for v in p.get("variants", []):
            total_v += 1
            bc = (v.get("barcode") or "").strip()
            if bc:
                with_bc += 1
                len_dist[len(bc)] += 1
                status_barcode[f"{st}+bc"] += 1
            else:
                status_barcode[f"{st}+无"] += 1
    print(f"page {page}: cum products={sum(vendor.values())} "
          f"variants={total_v} with_bc={with_bc}", flush=True)
    page += 1
    since = batch[-1]["id"]
    time.sleep(0.45)

print("\n=== vendor 分布 ===")
for k, n in vendor.most_common(10):
    print(f"  {k}: {n}")
print("\n=== 商品状态 ===", dict(prod_status))
print(f"\n=== 变体 barcode === 总数 {total_v}，非空 {with_bc} "
      f"(基线 13,533)")
print("  长度分布:", dict(len_dist.most_common()))
print("  状态交叉:", dict(status_barcode.most_common()))
client.close()
