# -*- coding: utf-8 -*-
"""抽样: cs_product 规格字段格式 + 现有产品描述结构。"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
for csid in ("CS-ZBR138BX", "CS-WRS300PW"):
    cc.execute(
        "SELECT cs_id,category,brand,part_no,dimension,battery_type,"
        "capacity,net_weight_g,voltage,wh_value,bar_code "
        "FROM cs_product WHERE cs_id=%s", (csid,))
    print(dict(zip(
        ["cs_id", "category", "brand", "part_no", "dimension",
         "battery_type", "capacity", "net_weight_g", "voltage",
         "wh_value", "bar_code"], cc.fetchone())))
cc.execute("SELECT COUNT(*) FROM cs_product WHERE wh_value IS NULL "
           "OR wh_value=''")
print("wh_value 空值行:", cc.fetchone()[0], "/ 22143")
cs.close()

cl = ShopifyRest(StoreService().get_client(1)).client
r = cl._client.get("products.json", params={
    "limit": 1, "handle": "battery-for-zebra-zr138-zr138cr-p1098850",
    "fields": "id,handle,body_html"}, auth=cl._auth)
ps = r.json()["products"]
if ps:
    b = ps[0]["body_html"] or ""
    print("\n描述长度:", len(b))
    print("描述前 500 字符:", b[:500])
else:
    print("按 handle 未取到, 用搜索")
