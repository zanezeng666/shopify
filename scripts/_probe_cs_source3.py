# -*- coding: utf-8 -*-
"""取证 3：category -> 尾段 N 众数映射 + 老产品 body_html 完整模板。只读。"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope

with get_cs_engine().connect() as c:
    rows = c.execute(text("SELECT cs_id, category FROM cs_product")).all()
cat_of = {}
for cs_id, cat in rows:
    cat_of[(cs_id or "").strip()] = (cat or "").strip()

with session_scope() as s:
    skus = [r[0] for r in s.execute(
        text("SELECT sku FROM product_variants WHERE store_id=1 AND sku LIKE 'CS-%'")
    ).all()]

pair = Counter()
for sku in skus:
    parts = sku.split("_")
    m = re.match(r"^(CS-[A-Za-z0-9]+)", sku)
    if not m or len(parts) < 4 or not parts[2].isdigit():
        continue
    pair[(cat_of.get(m.group(1), "?"), int(parts[2]))] += 1

cat_n: dict[str, tuple[int, int, int]] = {}
by_cat = defaultdict(Counter)
for (cat, n), cnt in pair.items():
    by_cat[cat][n] += cnt
for cat, ctr in by_cat.items():
    top = ctr.most_common(1)[0]
    total = sum(ctr.values())
    cat_n[cat] = (top[0], top[1], total)
print("category -> N 映射（N, 命中数, 总数）:")
for cat, (n, hitc, total) in sorted(cat_n.items(), key=lambda x: -x[1][2]):
    print(f"  {cat!r}: N={n} ({hitc}/{total})")

# 老产品完整 body 模板（多取两个不同类目）
with session_scope() as s:
    r = s.execute(text(
        "SELECT p.title, p.raw FROM products p JOIN product_variants v ON v.product_id=p.id "
        "WHERE v.store_id=1 AND v.sku LIKE 'CS-TMS20SL%' LIMIT 1"
    )).first()
title, raw = r
body = (raw or {}).get("body_html") or ""
print(f"\n=== 老 body 完整（title={title[:60]}）共 {len(body)} 字符 ===")
print(body)
Path("_old_body_sample.txt").write_text(body, encoding="utf-8")
