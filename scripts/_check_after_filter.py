# -*- coding: utf-8 -*-
"""过滤后核查：剩余 N=0 构成 + 新电池类目（Electric eBike 等）确认进 to_create（只读）。"""
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

catalog = svc.load_cs_catalog()
cat_of = {}
for (csid, bl), row in catalog.items():
    cat_of[(csid, bl)] = row["category"]

n_zero, cats_new = [], Counter()
for it in items:
    n = int(it["sku"].split("_")[2])
    cat = cat_of.get((it["cs_id"], it["brand"].lower()))
    if n == 0:
        n_zero.append((it["sku"], cat))
        cats_new[cat] += 1

mapped_zero = [(s, c) for s, c in n_zero if c in _CATEGORY_SKU_CODE]
unmapped = [(s, c) for s, c in n_zero if c not in _CATEGORY_SKU_CODE]
print(f"N=0 共 {len(n_zero)}：映射内真 0 码 {len(mapped_zero)} + 未映射新类目 {len(unmapped)}")
print("未映射类目分布:", dict(cats_new.most_common(15)))
print("映射内 0 码样本:", mapped_zero[:4])

ebike = [i for i in items if i["cs_id"].startswith("CS-EB") or "eBike" in (cat_of.get((i["cs_id"], i["brand"].lower())) or "")]
print("Electric eBike 类目进 to_create 数:", len(ebike))
for i in items:
    if cat_of.get((i["cs_id"], i["brand"].lower())) == "Electric eBike":
        print("  样例:", i["sku"], "|", i["title"][:60])
        break
