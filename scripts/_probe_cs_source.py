# -*- coding: utf-8 -*-
"""取证 CS 源头结构：cs_product 表是否有同 cs_id 多行（每品牌一行）。只读。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    cols = c.execute(text("SHOW COLUMNS FROM cs_product")).all()
    print("columns:", [(r[0], r[1]) for r in cols])

    n_all, n_distinct = c.execute(
        text("SELECT COUNT(*), COUNT(DISTINCT cs_id) FROM cs_product")
    ).one()
    print(f"rows={n_all} distinct_cs_id={n_distinct} -> 同 cs_id 多行: {n_all - n_distinct}")

    for cs in ("CS-AYD1CL", "CS-PHD600MB", "CS-TMS20SL"):
        rows = c.execute(
            text("SELECT * FROM cs_product WHERE cs_id = :x"), {"x": cs}
        ).all()
        print(f"\n=== {cs}: {len(rows)} rows")
        col_names = [r[0] for r in cols]
        for r in rows[:6]:
            d = dict(zip(col_names, r))
            print({k: (str(v)[:60] if v is not None else None) for k, v in d.items()})

    # 重复 cs_id 的分布（多少个 cs_id 有几行）
    dup = c.execute(text(
        "SELECT n, COUNT(*) AS cnt FROM (SELECT cs_id, COUNT(*) AS n FROM cs_product GROUP BY cs_id) t "
        "GROUP BY n ORDER BY n"
    )).all()
    print("\n每 cs_id 行数分布:", [(int(a), int(b)) for a, b in dup])
