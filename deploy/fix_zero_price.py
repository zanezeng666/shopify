# -*- coding: utf-8 -*-
"""asus 组 $0 变体：源库建议价可救则救，否则删变体。"""
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
cc.execute("""SELECT cs_id, suggested_retail_price, capacity
              FROM cs_product WHERE cs_id IN ('CS-AUA7DT','CS-AUA7XB',
              'CS-AUA7HB')""")
src = {r[0]: (r[1], r[2]) for r in cc.fetchall()}
cs.close()
for k, (p, c) in src.items():
    print(f"{k}: cap={c} suggested=${p}")

cl = ShopifyRest(StoreService().get_client(1)).client
p = cl.request("GET", "products.json", params={
    "limit": 5, "handle": "battery-for-asus-eee-pc-703-eee-pc-900a-eee-pc-900ha"
                           "-eee-pc-900hd-eee-pc-900-bk010x-eee-pc-900-bk041",
    "fields": "id,variants"}).get("products", [])
if not p:
    prods = cl.request("GET", "products.json", params={
        "limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
        "fields": "id,handle,variants", "status": "active"}).get("products", [])
    p = [x for x in prods if x["handle"].startswith("battery-for-asus-eee-pc-703")]
tgt = p[0]
for v in tgt["variants"]:
    if float(v["price"] or 0) != 0:
        continue
    sku = v.get("sku") or ""
    cs_id = sku.split("_")[0]
    sug = src.get(cs_id, (None,))[0]
    if sug and float(sug) > 0:
        cl.request("PUT", f"variants/{v['id']}.json", json_body={
            "variant": {"id": v["id"], "price": f"{float(sug):.2f}"}})
        print(f"fix {v['option1']}: $0 -> ${sug}")
    else:
        cl.request("DELETE", f"variants/{v['id']}.json")
        print(f"del {v['option1']}: 源库也无建议价")
print("终态:", [(x["option1"], x["price"])
      for x in cl.request("GET", f"products/{tgt['id']}.json",
                          params={"fields": "variants"})["product"]["variants"]])
