# -*- coding: utf-8 -*-
"""核查 cs_id 前缀分布 + 充电器类目记录的 title 形态（只读）。"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shopify_admin.services.products.sync_shopify import (
    CsShopifySyncService, build_new_product_payload,
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

print()
# 充电器/适配器类目样本：title 形态是否违和（Battery for ... Charger）
charger_cats = {"Battery Charger", "Camera Charger", "Power Tools Charger",
                "Laptop Adapter", "Mobile Phone Charger", "Barcode Scanner Charger"}
n = 0
for k, v in catalog.items():
    if v["category"] in charger_cats and n < 6:
        p = svc.build_new_product_payload(v)
        print(f"[{v['category']}] title={p['title'][:90]}")
        print(f"    part_no={v['part_no']!r} fit={v['fit_model'][:70]!r}")
        n += 1
