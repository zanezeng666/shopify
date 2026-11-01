# -*- coding: utf-8 -*-
"""细化分析：条码漂移形态 + 待发布新品素材质量（只读）。"""
from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope
from shopify_admin.models.product import ProductVariant

CS_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")

# cs_id -> (bar_code, status, brand, part_no, fit_model, capacity, voltage, battery_type, retail)
with get_cs_engine().connect() as c:
    rows = c.execute(text(
        "SELECT cs_id, bar_code, status, brand, part_no, fit_model, capacity, "
        "voltage, battery_type, suggested_retail_price FROM cs_product"
    )).all()
cs = {r[0].strip(): r for r in rows if r[0]}
on_sale = {k: v for k, v in cs.items() if int(v[2] or 0) == 1}

with session_scope() as s:
    variants = [((v.sku or "").strip(), (v.barcode or "").strip())
                for v in s.query(ProductVariant.sku, ProductVariant.barcode).all()]

anchored: dict[str, list] = {}
for sku, barcode in variants:
    m = CS_RE.match(sku)
    if m:
        anchored.setdefault(m.group(1), []).append((sku, barcode))

# ---- 条码漂移形态 ----
fill_ok = conflict = both_empty = 0
conflict_samples = []
for csid, vs in anchored.items():
    src = cs.get(csid)
    if src is None:
        continue
    bar_src = str(src[1] or "").strip()
    for _sku, barcode in vs:
        if not bar_src and not barcode:
            both_empty += 1
        elif not barcode and bar_src:
            fill_ok += 1          # 店铺空 CS 有 -> 补齐型
        elif barcode and bar_src and barcode != bar_src:
            conflict += 1         # 都有但不同 -> 冲突型
            if len(conflict_samples) < 8:
                conflict_samples.append((_sku, barcode, bar_src))

print(f"[条码漂移形态] 补齐型(店铺空·CS有)={fill_ok}  冲突型(都有但不同)={conflict}  双空={both_empty}")
for s_ in conflict_samples:
    print(f"  冲突例: {s_[0]}  店铺={s_[1]}  CS={s_[2]}")

# ---- 待发布新品素材质量 ----
to_publish = [k for k in on_sale if k not in anchored]
has_price = [k for k in to_publish if Decimal(str(on_sale[k][9] or 0)) > 0]
has_fit = [k for k in to_publish if (on_sale[k][5] or "").strip()]
has_brand = [k for k in to_publish if (on_sale[k][3] or "").strip()]
print(f"\n[待发布 {len(to_publish)}] 有建议零售价={len(has_price)}  有适配机型={len(has_fit)}  有品牌={len(has_brand)}")
print("\n素材样例（前 6 个）：")
for k in to_publish[:6]:
    r = on_sale[k]
    print(f"  {k}: brand={r[3]!r} part_no={r[4]!r} fit_model={str(r[5])[:70]!r} "
          f"cap={r[6]!r} volt={r[7]!r} type={r[8]!r} retail={r[9]}")

# ---- 既有产品标题风格（新品命名参考） ----
print("\n[既有变体 SKU 后缀结构样例]")
for csid, vs in list(anchored.items())[:6]:
    for sku, _ in vs[:2]:
        print(f"  {sku}")
