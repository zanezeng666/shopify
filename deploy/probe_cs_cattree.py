# -*- coding: utf-8 -*-
"""查 CS 源库类目树：Medical Battery 父子关系的真实存储。"""
import os
import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

conn = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ["CS_DB_PORT"]),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cur = conn.cursor()

print("== 1) 类目相关表 ==")
cur.execute("SHOW TABLES")
tables = [r[0] for r in cur.fetchall()]
cat_tables = [t for t in tables if any(k in t.lower() for k in
              ("categor", "cate", "tree", "class"))]
print(cat_tables or "（无类目专用表）")

print("\n== 2) cs_product 类目相关字段 ==")
cur.execute("SHOW COLUMNS FROM cs_product")
cols = [(r[0], r[1]) for r in cur.fetchall()
        if any(k in r[0].lower() for k in ("cat", "type", "parent"))]
print(cols)

print("\n== 3) 用户所见 7 个子类在 cs_product.category 的分布 ==")
for v in ("Electronic Magnifier", "Medical", "Microscope", "Shaver",
          "Thermal Electric", "Toothbrush", "Personal Care"):
    cur.execute("SELECT COUNT(*) FROM cs_product WHERE category=%s", v)
    print(f"  {v:24} {cur.fetchone()[0]:>6} 个产品")
cur.execute("SELECT COUNT(*) FROM cs_product WHERE category='Medical'")
print(f"  （对照）Medical Battery 类产品数见上表 Medical 行")

print("\n== 4) 是否存在父类目字段/映射 ==")
for t in cat_tables:
    cur.execute(f"SHOW COLUMNS FROM `{t}`")
    print(f"  {t}: {[r[0] for r in cur.fetchall()][:12]}")

conn.close()
