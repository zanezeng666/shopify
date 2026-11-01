# -*- coding: utf-8 -*-
"""to_create 记录的 category 分布（补 _CATEGORY_SKU_CODE 缺口）。只读。"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import shopify_admin.services.products.sync_shopify as sync_mod
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

svc = CsShopifySyncService()
c = svc._compute(1)
cats = Counter()
for item in c["to_create"]:
    row = c["catalog"].get((item["cs_id"], (item.get("brand") or "").lower()))
    cats[row and row.get("category")] += 1
mapped = sync_mod._CATEGORY_SKU_CODE
print("to_create 类目分布（* = 未映射）:")
for cat, n in cats.most_common(40):
    mark = "" if cat in mapped else " *"
    print(f"  {cat!r}: {n}{mark}")
