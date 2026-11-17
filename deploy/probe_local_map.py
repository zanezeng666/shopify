# -*- coding: utf-8 -*-
"""本地库 products/product_variants 字段 + 映射链。"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

conn = pymysql.connect(
    host=os.environ["SHOPIFY_DB_HOST"],
    port=int(os.environ.get("SHOPIFY_DB_PORT", 3306)),
    user=os.environ["SHOPIFY_DB_USER"],
    password=os.environ["SHOPIFY_DB_PASSWORD"],
    database=os.environ["SHOPIFY_DB_NAME"], charset="utf8mb4")
cur = conn.cursor()

for t in ("products", "product_variants"):
    cur.execute(f"SHOW COLUMNS FROM {t}")
    print(f"== {t} ==", [r[0] for r in cur.fetchall()])
    cur.execute(f"SELECT COUNT(*) FROM {t}")
    print("  行数:", cur.fetchone()[0])

# 看样例找 cs 关联
cur.execute("SELECT * FROM products LIMIT 1")
row = cur.fetchone()
cur.execute("SHOW COLUMNS FROM products")
cols = [r[0] for r in cur.fetchall()]
print("\nproducts 样例:")
for c, v in zip(cols, row):
    print(f"  {c} = {str(v)[:60]!r}")
conn.close()
