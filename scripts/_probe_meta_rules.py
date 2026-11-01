# -*- coding: utf-8 -*-
"""探查存量规则：product_type 分布 / tags 来源 / SKU 品牌段字符规则（只读）。"""
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import session_scope

with session_scope() as s:
    rows = s.execute(text(
        "SELECT p.product_type, p.tags, v.sku FROM products p "
        "JOIN product_variants v ON v.shopify_product_id = p.shopify_product_id "
        "AND v.store_id = p.store_id "
        "WHERE v.sku LIKE 'CS-%' AND v.sku LIKE '%\\_%' "
        "AND p.product_type IS NOT NULL LIMIT 20000")).all()

pt = Counter(r[0] for r in rows)
print("product_type 分布 top20:", pt.most_common(20))
print("product_type 空值数(样本内):", sum(1 for r in rows if not r[0]))

# tags 规则：老品 tags vs title
import json
with session_scope() as s:
    sample = s.execute(text(
        "SELECT p.title, p.tags FROM products p "
        "JOIN product_variants v ON v.shopify_product_id = p.shopify_product_id "
        "AND v.store_id = p.store_id "
        "WHERE v.sku LIKE 'CS-%' LIMIT 8")).all()
for t, tg in sample:
    print(f"  title={t[:60]!r}\n    tags={tg[:100]!r}")

# SKU 品牌段字符规则
seg = Counter()
bad = []
for _, _, sku in rows[:20000]:
    parts = sku.split("_")
    if len(parts) >= 4:
        b = parts[1]
        if not re.fullmatch(r"[A-Za-z0-9]+", b):
            bad.append(sku)
print(f"\n样本 {min(len(rows),20000)} 个 4 段 SKU：品牌段非纯字母数字 = {len(bad)}")
print("  样例:", bad[:10])
