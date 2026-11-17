# -*- coding: utf-8 -*-
"""试点残留修复：按分组重算每容量代表，全覆盖校准主品变体(price/sku/grams)。
兼作全量脚本的校准模块原型。"""
import os
import sys
from collections import defaultdict

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
cc.execute("SELECT cs_id, part_no, fit_model, capacity FROM cs_product")
groups = defaultdict(list)
for cs_id, pn, fm, cap in cc.fetchall():
    if pn and fm:
        groups[(pn, fm)].append((cs_id, cap))
cs.close()

csid2cap, gid_of = {}, {}
for gi, (k, mem) in enumerate(groups.items()):
    for cs_id, cap in mem:
        csid2cap[cs_id] = cap
        gid_of[cs_id] = gi

cl = ShopifyRest(StoreService().get_client(1)).client

TARGETS = [15485325312244, 15484830548212]   # aisino / dewalt 主品

for pid in TARGETS:
    p = cl.request("GET", f"products/{pid}.json",
                   params={"fields": "id,handle,title,variants"}).get("product", {})
    main_sku = next((v["sku"] for v in p["variants"] if v.get("sku")), "")
    main_gid = gid_of.get(main_sku.split("_")[0]) if main_sku else None
    if main_gid is None:
        print(f"! {pid} 找不到分组"); continue

    # 拉本组全部 cs_id（被删页价格不可查，sku 用主品品牌段重构）
    g_csids = []
    for gi2, (k, mem) in enumerate(groups.items()):
        if gi2 == main_gid:
            g_csids = [c for c, _ in mem]
    print(f"\n== {p['handle'][:55]}  组内 cs_id {len(g_csids)} 个")

    # 每容量代表: 源库 cs_id 顺序优先 + 线上已知价格
    # 被删页价格已不可查，用现存活页价格；sku 用 cs_id 重构品牌段未知 -> 用主品 sku 的品牌段
    brand_seg = "_".join(main_sku.split("_")[1:]) if main_sku else ""
    for v in p["variants"]:
        cap = v["option1"]
        want_price = v["price"]
        # 从源库找该容量 cs_id
        rep = next((c for c in g_csids if csid2cap.get(c) == cap), None)
        if not rep:
            print(f"  ? {cap} 无源 cs_id，跳过")
            continue
        sku = f"{rep}_{brand_seg}" if brand_seg else rep
        if v.get("sku") != sku or float(v["price"]) == 0:
            cl.request("PUT", f"variants/{v['id']}.json", json_body={
                "variant": {"id": v["id"], "sku": sku}})
            print(f"  fix {cap}: sku={sku}")

# dewalt 3000 错价单独修
p = cl.request("GET", "products/15484830548212.json",
               params={"fields": "variants"}).get("product", {})
for v in p["variants"]:
    if v["option1"] == "3000mAh" and float(v["price"]) != 84.78:
        cl.request("PUT", f"variants/{v['id']}.json", json_body={
            "variant": {"id": v["id"], "price": "84.78"}})
        print(f"\ndewalt 3000mAh 价格 {v['price']} -> 84.78")
