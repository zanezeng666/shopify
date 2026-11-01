# -*- coding: utf-8 -*-
"""范围探查：cs_id 前缀 + 全部类目清单（区分已映射/未命中）+ 非电池类目字段特征（只读）。"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import (
    _CATEGORY_SKU_CODE, CsShopifySyncService,
)

svc = CsShopifySyncService()
catalog = svc.load_cs_catalog()

pref = Counter(k[0].split("-")[0] for k in catalog)
print("cs_id 前缀分布:", dict(pref.most_common(10)))
non_cs = [(k, v) for k, v in catalog.items() if not k[0].startswith("CS-")]
print("非 CS- 前缀记录数:", len(non_cs))
for k, v in non_cs[:5]:
    print(" ", k[0], "|", v["brand"], "|", v["category"], "|",
          (v["fit_model"] or "")[:60])

print("\n=== 全部类目（未命中映射的标 *）===")
cats = Counter()
for k, v in catalog.items():
    cats[v["category"] or "(空)"] += 1
for cat, cnt in cats.most_common():
    flag = "" if cat in _CATEGORY_SKU_CODE or cat == "(空)" else " *未映射*"
    print(f"  {cnt:5d}  {cat}{flag}")

print("\n=== 非电池嫌疑类目样本（字段特征）===")
suspect = ["Battery Charger", "Camera Charger", "Laptop Adapter",
           "DC Coupler", "Cosmetic Mirror", "Two-Way Radio Case"]
for cat in suspect:
    rows = [v for v in catalog.values() if v["category"] == cat][:2]
    for v in rows:
        print(f"[{cat}] cs_id={v['cs_id']} type={v['battery_type']!r} "
              f"cap={v['capacity']!r} part={v['part_no'][:40]!r}")
print("\n=== 电池类目 battery_type 对照 ===")
for cat in ["Mobile, SmartPhone", "Notebook, Laptop", "Camera"]:
    rows = [v for v in catalog.values() if v["category"] == cat][:2]
    for v in rows:
        print(f"[{cat}] cs_id={v['cs_id']} type={v['battery_type']!r} cap={v['capacity']!r}")
