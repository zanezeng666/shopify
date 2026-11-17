# -*- coding: utf-8 -*-
"""验证 cs_product 多行 cs_id 与 Arnagar 组真实 key。"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

cc.execute("SELECT COUNT(*) FROM (SELECT cs_id FROM cs_product "
           "GROUP BY cs_id HAVING COUNT(*)>1) t")
print("多行 cs_id 数:", cc.fetchone()[0])

cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product "
           "WHERE cs_id IN ('CS-PCM720VX','CS-PCM710VX')")
for r in cc.fetchall():
    print("Arnagar 行:", r)

# S8 fit_model 的行分布
cc.execute("SELECT cs_id, part_no, fit_model FROM cs_product "
           "WHERE fit_model='S8,S8 pro' LIMIT 40")
rows = cc.fetchall()
print(f"fit_model='S8,S8 pro' 行数(前40): {len(rows)}")
for r in rows[:8]:
    print("  ", r)
cs.close()
