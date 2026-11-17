# -*- coding: utf-8 -*-
"""查源库可用规格字段 + 当前产品描述结构样例。"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SHOW TABLES")
tables = [x[0] for x in cc.fetchall()]
print("源库表:", tables)
for t in tables:
    if t == "cs_inventory":
        continue
    cc.execute(f"DESCRIBE `{t}`")
    cols = [x[0] for x in cc.fetchall()]
    cc.execute(f"SELECT COUNT(*) FROM `{t}`")
    n = cc.fetchone()[0]
    print(f"\n{t} ({n}行): {cols}")
cs.close()
