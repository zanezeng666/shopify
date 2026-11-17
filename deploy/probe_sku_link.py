# -*- coding: utf-8 -*-
"""排查 cs_id -> sku 映射断点。"""
import os

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")

main = pymysql.connect(
    host=os.environ["SHOPIFY_DB_HOST"],
    port=int(os.environ.get("SHOPIFY_DB_PORT", 3306)),
    user=os.environ["SHOPIFY_DB_USER"],
    password=os.environ["SHOPIFY_DB_PASSWORD"],
    database=os.environ["SHOPIFY_DB_NAME"], charset="utf8mb4")
mc = main.cursor()

mc.execute("SELECT sku FROM product_variants WHERE sku LIKE 'CS-%' LIMIT 5")
print("CS- 开头 sku 样例:", [r[0] for r in mc.fetchall()])
mc.execute("SELECT COUNT(*) FROM product_variants WHERE sku LIKE 'CS-%'")
print("CS- sku 数:", mc.fetchone()[0])

mc.execute("SELECT sku FROM product_variants WHERE sku IS NOT NULL "
           "AND sku != '' LIMIT 8")
print("sku 杂样:", [r[0] for r in mc.fetchall()])

mc.execute("""SELECT p.status, COUNT(DISTINCT p.shopify_product_id)
              FROM products p WHERE p.shopify_product_id IN (
                SELECT DISTINCT shopify_product_id FROM product_variants
                WHERE sku LIKE 'CS-%')
              GROUP BY p.status""")
print("含 CS sku 的产品 status:", mc.fetchall())
main.close()

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id FROM cs_product LIMIT 5")
print("cs_product.cs_id 样例:", [r[0] for r in cc.fetchall()])
cs.close()
