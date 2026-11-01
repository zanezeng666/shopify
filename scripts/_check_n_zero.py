# -*- coding: utf-8 -*-
"""全量核查 to_create 的 SKU 尾段 N 分布与未命中类目（只读）。"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import (
    _CATEGORY_SKU_CODE, CsShopifySyncService,
)

svc = CsShopifySyncService()
d = svc.diff(1, sample=None)
items = d["plan"]["to_create"]["items"]
print("to_create =", len(items))

n_zero, unmapped = [], Counter()
cat_by_rec = {}
catalog = CsShopifySyncService.load_cs_catalog()
for it in items:
    n = int(it["sku"].split("_")[2])
    if n == 0:
        n_zero.append(it["sku"])
    for (csid, bl), row in catalog.items():
        if csid == it["cs_id"] and bl == it["brand"].lower():
            cat_by_rec[(csid, bl)] = row["category"]
            break

for (csid, bl), cat in cat_by_rec.items():
    if cat not in _CATEGORY_SKU_CODE:
        unmapped[cat] += 1

print("N=0 count =", len(n_zero))
print("N=0 sample:", n_zero[:8])
print("unmapped categories in to_create:", dict(unmapped.most_common(20)))
mapped_zero = [s for s in n_zero
               if cat_by_rec.get((s.split("_")[0], s.split("_")[1].lower()))
               in _CATEGORY_SKU_CODE]
print("N=0 but category mapped (real code 0):", len(mapped_zero), mapped_zero[:6])
