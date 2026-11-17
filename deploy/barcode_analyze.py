# -*- coding: utf-8 -*-
"""分析主图条码扫描结果: 类型/匹配CS-EAN/品类分布。"""
import json
from collections import Counter
from pathlib import Path

import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import create_engine, text
from shopify_admin.core.database import get_engine

rows = [json.loads(l) for l in open(
    "/home/jason/shopify-admin/deploy/barcode_scan_result.jsonl", encoding="utf-8")]
print(f"检出条码主图: {len(rows)} 张")

# 1) 条码类型分布
fmt = Counter()
for r in rows:
    for v, f in r["codes"]:
        fmt[f] += 1
print("类型分布:", dict(fmt))

# 2) 解码值是否匹配源库 CS EAN (bar_code)
eng = get_engine()
with eng.connect() as conn:
    all_eans = set(x[0] for x in conn.execute(
        text("SELECT bar_code FROM cs_product WHERE bar_code IS NOT NULL")))

hit = miss = 0
cats = Counter()
for r in rows:
    for v, f in r["codes"]:
        if v in all_eans:
            hit += 1
        else:
            miss += 1
    # 品类: title 里第一个设备品牌词
    t = r["title"].lower()
    for k in ["zebra", "motorola", "honeywell", "tomtom", "oral-b",
              "intermec", "dymo", "zebra", "symbol", "datalogic", "uniden"]:
        if k in t:
            cats[k] += 1
            break
    else:
        cats["other"] += 1

print(f"解码值匹配CS-EAN: {hit} | 不匹配: {miss}")
print("品类分布:", dict(cats.most_common(12)))

# 3) 抽3条不匹配的看看(可能是其他码: ISBN/Code128 等)
shown = 0
for r in rows:
    for v, f in r["codes"]:
        if v not in all_eans and shown < 5:
            print("  不匹配样例:", f, v, "|", r["title"][:45])
            shown += 1
