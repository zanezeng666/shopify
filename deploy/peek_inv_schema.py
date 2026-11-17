# -*- coding: utf-8 -*-
import os

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SHOW COLUMNS FROM cs_inventory")
for r in cc.fetchall():
    print(r[0], r[1])
cc.execute("SELECT * FROM cs_inventory LIMIT 3")
cols = [d[0] for d in cc.description]
for row in cc.fetchall():
    print(dict(zip(cols, row)))
cs.close()
