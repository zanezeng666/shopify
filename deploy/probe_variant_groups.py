# -*- coding: utf-8 -*-
"""按 (fit_model, part_no) 分组统计容量差异组 = 变体合并候选。"""
import os
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

conn = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cur = conn.cursor()

cur.execute("SELECT cs_id, part_no, fit_model, capacity, category, status "
            "FROM cs_product")
rows = cur.fetchall()

groups = defaultdict(list)
for cs_id, part_no, fit_model, cap, cat, st in rows:
    key = (part_no or "", fit_model or "")
    groups[key].append((cs_id, cap, cat, st))

multi = {k: v for k, v in groups.items()
         if len({c for _, c, _, _ in v if c}) >= 2}
n_products = sum(len(v) for v in multi.values())
print(f"总产品 {len(rows)} | 分组 {len(groups)} | 容量差异组 {len(multi)}"
      f" | 涉及产品 {n_products}")

# 容量取值形态
caps = defaultdict(int)
for _, v in groups.items():
    for _, c, _, _ in v:
        caps[bool(c)] += 1
print(f"capacity 空/非空: 空={caps.get(False,0)} 非空={caps.get(True,0)}")

# 分布直方
dist = defaultdict(int)
for v in multi.values():
    dist[len({c for _, c, _, _ in v if c})] += 1
print("组内容量种数分布:", dict(sorted(dist.items())))

print("\n== 样例组（前 5） ==")
for i, (k, v) in enumerate(multi.items()):
    if i >= 5:
        break
    pn, fm = k
    print(f"\n[{i+1}] part_no={str(pn)[:40]!r} category={v[0][2]}")
    print(f"    fit_model={str(fm)[:80]!r}...")
    for cs_id, cap, _, _ in sorted(v, key=lambda x: x[1] or ""):
        print(f"    - {cs_id}  cap={cap!r}")

# 单容量组（不合并的）
print("\n单一容量组(不变):", len(groups) - len(multi))
conn.close()
