# -*- coding: utf-8 -*-
"""二合一: ①源库 EAN 批量补写 Shopify 变体 barcode(GTIN) ②feed 就绪度摸底。
只补空缺不覆盖已有, 幂等可重跑。"""
import os
import time

import httpx
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
cl = ShopifyRest(StoreService().get_client(1)).client

# 预载全源库 cs_id -> (bar_code, capacity, voltage)
cc.execute("SELECT cs_id, bar_code, capacity, voltage, net_weight_g, "
           "battery_type FROM cs_product")
src = {}
for csid, bc, cap, volt, wg, bt in cc.fetchall():
    if bc and len(str(bc)) >= 12:
        src[csid] = {"gtin": str(bc), "cap": cap or "", "volt": volt or "",
                     "wg": wg, "bt": bt or ""}
cs.close()
print(f"源库可用 EAN: {len(src)} 个 cs_id")

params = {"limit": 250, "status": "active",
          "fields": "id,handle,vendor,product_type,title,images,variants"}
allp, page = [], 0
while True:
    time.sleep(1.0)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    batch = r.json()["products"]
    allp += batch
    page += 1
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print(f"全店产品: {len(allp)} 个 ({page} 页)")

stat = {"变体总数": 0, "已有GTIN": 0, "补写成功": 0, "补写失败": 0,
        "源无码": 0, "无sku": 0, "无价格": 0, "无克重": 0, "无图": 0,
        "无vendor": 0}
for p in allp:
    if not p.get("vendor"):
        stat["无vendor"] += 1
    if not p.get("images"):
        stat["无图"] += 1
    for v in p["variants"]:
        stat["变体总数"] += 1
        if not (v.get("price") and float(v["price"]) > 0):
            stat["无价格"] += 1
        if not v.get("grams"):
            stat["无克重"] += 1
        sku = v.get("sku") or ""
        csid = sku.split("_")[0]
        if not csid.startswith("CS-"):
            stat["无sku"] += 1
            continue
        if v.get("barcode"):
            stat["已有GTIN"] += 1
            continue
        s = src.get(csid)
        if not s:
            stat["源无码"] += 1
            continue
        try:
            time.sleep(0.35)
            r2 = cl._client.put(f"variants/{v['id']}.json", auth=cl._auth,
                                json={"variant": {"id": v["id"],
                                                  "barcode": s["gtin"]}})
            r2.raise_for_status()
            stat["补写成功"] += 1
        except Exception as ex:
            stat["补写失败"] += 1
            if stat["补写失败"] <= 3:
                print("写失败样例:", v["id"], str(ex)[:100])

print("\n===== feed 就绪度 & GTIN 补写结果 =====")
for k, n in stat.items():
    print(f"{k}: {n}")
tot = stat["变体总数"]
cov = stat["已有GTIN"] + stat["补写成功"]
if tot:
    print(f"GTIN 覆盖率: {cov}/{tot} = {cov*100//tot}%")
