# -*- coding: utf-8 -*-
"""取证 2：cs_product 唯一键 / SKU 品牌段对齐率 / 尾段 N 与电压·类目关联。只读。"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope

with get_cs_engine().connect() as c:
    idx = c.execute(text("SHOW INDEX FROM cs_product")).all()
    print("indexes:", [(r[2], r[4], r[1]) for r in idx])
    dup_pairs = c.execute(text(
        "SELECT cs_id, brand, COUNT(*) n FROM cs_product GROUP BY cs_id, brand HAVING n > 1 LIMIT 5"
    )).all()
    print("同(cs_id,brand)重复行样例:", [(r[0], r[1], int(r[2])) for r in dup_pairs])
    # 同 cs_id 内 brand 聚合
    cs_rows = c.execute(text("SELECT cs_id, brand, category, voltage FROM cs_product")).all()

cs_brand: dict[str, set[str]] = defaultdict(set)
cs_volt: dict[str, str] = {}
cs_cat: dict[str, str] = {}
for cs_id, brand, cat, volt in cs_rows:
    k = (cs_id or "").strip()
    cs_brand[k].add((brand or "").strip().lower())
    cs_volt[k] = (volt or "").strip()
    cs_cat[k] = (cat or "").strip()

with session_scope() as s:
    skus = [r[0] for r in s.execute(
        text("SELECT sku FROM product_variants WHERE store_id=1 AND sku LIKE 'CS-%'")
    ).all()]

hit = miss = 0
miss_ex = []
tail_volt = defaultdict(Counter)   # 尾段N -> 电压分布
tail_cat = defaultdict(Counter)    # 尾段N -> 类目分布
for sku in skus:
    parts = sku.split("_")
    m = re.match(r"^(CS-[A-Za-z0-9]+)", sku)
    if not m or len(parts) < 2:
        continue
    cs_id, bseg = m.group(1), parts[1].lower()
    if bseg in cs_brand.get(cs_id, set()):
        hit += 1
    else:
        miss += 1
        if len(miss_ex) < 8:
            miss_ex.append(sku)
    if len(parts) >= 4 and parts[2].isdigit():
        tail_volt[int(parts[2])][cs_volt.get(cs_id, "?")] += 1
        tail_cat[int(parts[2])][cs_cat.get(cs_id, "?")] += 1

print(f"\nSKU 品牌段 vs cs_product.brand 对齐: hit={hit} miss={miss} ({miss_ex})")

print("\n尾段 N -> 电压 Top3（N=5,9,12,27,43,47,50,55,69,75,77）:")
for n in (5, 9, 12, 27, 43, 47, 50, 55, 69, 75, 77):
    print(f"  N={n}: volts={tail_volt[n].most_common(3)} cats={tail_cat[n].most_common(2)}")
