# -*- coding: utf-8 -*-
"""用 cs_product 现行 category 文本重建 N 映射（键=CS 当前写法），输出引擎常量字面量。只读。"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope

with get_cs_engine().connect() as c:
    rows = c.execute(text("SELECT cs_id, brand, category FROM cs_product")).all()
cat_exact: dict[tuple, str] = {}
by_cs: dict[str, list[str]] = {}
for cs_id, brand, cat in rows:
    k = ((cs_id or "").strip(), (brand or "").strip().lower())
    cat_exact[k] = (cat or "").strip()
    by_cs.setdefault((cs_id or "").strip(), []).append((brand or "").strip().lower())

def cat_of(csid: str, bseg: str) -> str | None:
    v = cat_exact.get((csid, bseg))
    if v is not None:
        return v
    bl = by_cs.get(csid) or []
    return cat_exact.get((csid, bl[0])) if len(bl) == 1 else None

with session_scope() as s:
    skus = [r[0] for r in s.execute(
        text("SELECT sku FROM product_variants WHERE store_id=1 AND sku LIKE 'CS-%'")
    ).all()]

by_cat = defaultdict(Counter)
for sku in skus:
    parts = sku.split("_")
    m = re.match(r"^(CS-[A-Za-z0-9]+)", sku)
    if not m or len(parts) < 4 or not parts[2].isdigit():
        continue
    cat = cat_of(m.group(1), parts[1].lower() if len(parts) >= 2 else "")
    if cat:
        by_cat[cat][int(parts[2])] += 1

out = ["_CATEGORY_SKU_CODE: dict[str, int] = {"]
covered = total = 0
for cat, ctr in sorted(by_cat.items(), key=lambda x: (-sum(x[1].values()), x[0])):
    n, hitc = ctr.most_common(1)[0]
    t = sum(ctr.values())
    total += t
    covered += hitc
    pct = hitc * 100 // t
    out.append(f'    "{cat}": {n},   # {hitc}/{t} ({pct}%)')
out.append("}")
Path("scripts/_catmap_literal.txt").write_text(
    "\n".join(out) + f"\n\n# total {covered}/{total}", encoding="utf-8")
print("\n".join(out[:12]))
print(f"... 共 {len(by_cat)} 类目，总命中 {covered}/{total}")
