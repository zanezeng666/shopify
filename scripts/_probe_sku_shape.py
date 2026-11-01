# -*- coding: utf-8 -*-
"""取证：店铺 CS 变体 SKU 形态分布 + 尾段规律 + 与 CS 记录品牌段对齐率。只读。"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope

with session_scope() as s:
    skus = [r[0] for r in s.execute(
        text("SELECT sku FROM product_variants WHERE store_id=1 AND sku LIKE 'CS-%'")
    ).all()]
print(f"CS 变体 SKU 总数: {len(skus)}")

seg_counts = Counter()
tails = Counter()
brand_seg_missing = 0
for sku in skus:
    parts = sku.split("_")
    seg_counts[len(parts)] += 1
    if len(parts) >= 2:
        tails["_".join(parts[2:])] += 1
    else:
        brand_seg_missing += 1
print("段数分布:", dict(sorted(seg_counts.items())))
print("无品牌段(裸CS-ID)数量:", brand_seg_missing)
print("尾段 Top15:", tails.most_common(15))

# 与 CS 记录对齐：SKU 品牌段能否在 cs_product 同 cs_id 行里找到
with get_cs_engine().connect() as c:
    rows = c.execute(text("SELECT cs_id, brand FROM cs_product")).all()
cs_brands: dict[str, set[str]] = {}
for cs_id, brand in rows:
    cs_brands.setdefault((cs_id or "").strip(), set()).add((brand or "").strip().lower())

hit = miss = 0
miss_examples = []
for sku in skus:
    parts = sku.split("_")
    m = re.match(r"^(CS-[A-Za-z0-9]+)", sku)
    if not m or len(parts) < 2:
        continue
    cs_id, bseg = m.group(1), parts[1].lower()
    if bseg in cs_brands.get(cs_id, set()):
        hit += 1
    else:
        miss += 1
        if len(miss_examples) < 10:
            miss_examples.append(sku)
print(f"\nSKU 品牌段 ↔ CS 记录 brand 对齐: hit={hit} miss={miss}")
print("miss 样例:", miss_examples)
