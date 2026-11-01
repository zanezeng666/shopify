# -*- coding: utf-8 -*-
"""验证假设：店铺 SKU 尾段 N == cs_product.series。只读。"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope

with get_cs_engine().connect() as c:
    rows = c.execute(text("SELECT cs_id, brand, series, color FROM cs_product")).all()
rec: dict[tuple, str] = {}
series_vals = Counter()
for cs_id, brand, series, color in rows:
    rec[(cs_id.strip(), (brand or "").strip().lower())] = (str(series or "").strip(), str(color or "").strip())
    series_vals[str(series or "").strip()] += 1

print("series 值域 Top20:", series_vals.most_common(20))

with session_scope() as s:
    skus = [r[0] for r in s.execute(
        text("SELECT sku FROM product_variants WHERE store_id=1 AND sku LIKE 'CS-%'")
    ).all()]

hit = miss = 0
miss_ex = []
for sku in skus:
    parts = sku.split("_")
    m = re.match(r"^(CS-[A-Za-z0-9]+)", sku)
    if not m or len(parts) < 4 or not parts[2].isdigit():
        continue
    n = parts[2]
    sv = rec.get((m.group(1), parts[1].lower()), (None, None))[0]
    if sv == n:
        hit += 1
    else:
        miss += 1
        if len(miss_ex) < 10:
            miss_ex.append((sku, sv))
print(f"尾段 N == series 命中: {hit}/{hit+miss}")
print("miss 样例 (sku, series):", miss_ex)
