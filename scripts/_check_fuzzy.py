# -*- coding: utf-8 -*-
"""模糊类目判别：capacity/battery_type 填充率 + 样本；AS- 前缀类目（只读）。"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import (
    _CATEGORY_SKU_CODE, CsShopifySyncService,
)

catalog = CsShopifySyncService.load_cs_catalog()

print("=== AS- 前缀记录 ===")
as_rows = [(k, v) for k, v in catalog.items() if k[0].startswith("AS-")]
for k, v in as_rows[:6]:
    print(f"  {k[0]} | {v['brand']} | {v['category']} | type={v['battery_type']!r} "
          f"cap={v['capacity']!r} part={v['part_no'][:36]!r}")

# 模糊类目：未映射 + 非充电器词
skip_kw = ("Charger", "Adapter", "Cable", "Case", "Coupler", "Mirror",
           "Microphone")
model_re = re.compile(r"^(?:\d{4,6}|ER\d+|CR\d+|EF\d+|AA|AAA)$")
fuzzy = {}
for k, v in catalog.items():
    cat = v["category"]
    if (cat in _CATEGORY_SKU_CODE or not cat or cat in ("Solar Battery",)
            or model_re.match(cat) or any(w.lower() in cat.lower() for w in skip_kw)
            or not k[0].startswith("CS-")):
        continue
    fuzzy.setdefault(cat, []).append(v)

print(f"\n=== 模糊类目（CS- 前缀、未映射、无充电器词）共 {len(fuzzy)} 个 ===")
for cat, rows in sorted(fuzzy.items(), key=lambda x: -len(x[1])):
    filled = sum(1 for r in rows if r["capacity"] or r["battery_type"])
    v = rows[0]
    print(f"  {len(rows):3d} [{filled:3d} 有容量] {cat!r} "
          f"type={v['battery_type']!r} cap={v['capacity']!r} part={v['part_no'][:30]!r}")
