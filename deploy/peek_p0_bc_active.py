# -*- coding: utf-8 -*-
"""P0-2a 追查：active 商品上残留的 163 个 barcode 是什么性质
- 12位(UPC) or 13位(EAN/Cameron Sino 残留)？
- 抽样值 + vendor 交叉 + 13位EAN在active里的确切数量
"""
import time
from collections import Counter

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
from shopify_admin.services.stores.service import StoreService  # noqa

client = StoreService().get_client(1)

samples = []
act_len = Counter()
act_vendor = Counter()
since = 0
while True:
    batch = client.request("GET", "products.json", params={
        "limit": 250, "since_id": since,
        "status": "active"}).get("products", [])
    if not batch:
        break
    for p in batch:
        for v in p.get("variants", []):
            bc = (v.get("barcode") or "").strip()
            if bc:
                act_len[len(bc)] += 1
                act_vendor[p.get("vendor") or "(空)"] += 1
                if len(samples) < 25:
                    samples.append((p.get("vendor"), v.get("sku"),
                                    bc, p.get("status")))
    since = batch[-1]["id"]
    time.sleep(0.45)

print("active 商品带码变体长度分布:", dict(act_len))
print("vendor 交叉:", dict(act_vendor))
print("\n抽样 25 条 (vendor | sku | barcode | status):")
for row in samples:
    print("  ", " | ".join(str(x) for x in row))
client.close()
