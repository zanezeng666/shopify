# -*- coding: utf-8 -*-
"""源库 net_weight_g 批量补写 Shopify 变体 grams (只补空缺, 幂等)。"""
import os
import time

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id, net_weight_g FROM cs_product WHERE net_weight_g > 0")
src = {a: int(b) for a, b in cc.fetchall()}
cs.close()
print(f"源库有克重: {len(src)} 个 cs_id")

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "status": "active", "fields": "id,variants"}
allp = []
while True:
    time.sleep(1.0)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

ok = fail = skip = 0
for p in allp:
    for v in p["variants"]:
        if v.get("grams"):
            continue
        csid = (v.get("sku") or "").split("_")[0]
        g = src.get(csid)
        if not g:
            skip += 1
            continue
        try:
            time.sleep(0.35)
            r2 = cl._client.put(f"variants/{v['id']}.json", auth=cl._auth,
                                json={"variant": {"id": v["id"], "grams": g}})
            r2.raise_for_status()
            ok += 1
        except Exception as ex:
            fail += 1
            if fail <= 3:
                print("失败样例:", v["id"], str(ex)[:100])
print(f"\n克重补写: 成功 {ok}, 失败 {fail}, 源无数据跳过 {skip}")
