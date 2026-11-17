# -*- coding: utf-8 -*-
"""探查 cs_product 结构，确认容量/电池型号/适配型号字段。"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

conn = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cur = conn.cursor()

cur.execute("SHOW FULL COLUMNS FROM cs_product")
print("== cs_product 字段 ==")
for r in cur.fetchall():
    print(f"  {r[0]:<24} {r[1]}")

cur.execute("SELECT COUNT(*) FROM cs_product")
print("\n总行数:", cur.fetchone()[0])
conn.close()
