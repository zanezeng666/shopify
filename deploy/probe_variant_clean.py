# -*- coding: utf-8 -*-
"""修正口径：排除空键组，挖 50 容量异常组，摸本地库映射链。"""
import os
from collections import defaultdict

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")

cur = cs.cursor()
cur.execute("SELECT cs_id, part_no, fit_model, capacity, category, status "
            "FROM cs_product")
rows = cur.fetchall()

groups = defaultdict(list)
for cs_id, part_no, fit_model, cap, cat, st in rows:
    groups[(part_no or "", fit_model or "")].append((cs_id, cap, cat, st))

def capset(v):
    return {c for _, c, _, _ in v if c}

# 异常组详情
print("== 大组(容量种数>=10) ==")
for k, v in groups.items():
    if len(capset(v)) >= 10:
        print(f"part_no={str(k[0])[:50]!r} fit_model={str(k[1])[:50]!r}")
        for cs_id, cap, cat, _ in list(v)[:8]:
            print(f"  - {cs_id} {cap!r} {cat}")
        print(f"  ... 共 {len(v)} 行 / {len(capset(v))} 种容量")

# 修正口径：排除 (part_no='' AND fit_model='')
clean = {k: v for k, v in groups.items()
         if k[0] and k[1] and len(capset(v)) >= 2}
n = sum(len(v) for v in clean.values())
print(f"\n修正后: 容量差异组 {len(clean)} | 涉及产品 {n}")
dist = defaultdict(int)
for v in clean.values():
    dist[len(capset(v))] += 1
print("组内容量种数:", dict(sorted(dist.items())))

# 本地库映射
main = pymysql.connect(
    host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", 3306)),
    user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"], charset="utf8mb4")
mc = main.cursor()
mc.execute("SHOW TABLES")
tables = [r[0] for r in mc.fetchall()]
print("\n主库表:", [t for t in tables if "product" in t.lower()][:8])
