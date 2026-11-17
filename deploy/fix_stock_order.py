# -*- coding: utf-8 -*-
"""试点 5 组：变体补库存（cs_inventory 口径）+ 容量从大到小重排。"""
import os
import re
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.services.inventory.service import InventoryService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

PREFIXES = [
    "battery-for-al-ko-comfort-gt-1825",
    "battery-for-sichler-reinigungs-roboter",
    "battery-for-asus-eee-pc-703",
    "battery-for-dewalt-20v-max-60v-max-120v",
    "battery-for-dolmar-ah-3756",
]

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,variants", "status": "active"}
allp = []
while True:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [x.split(";")[0].strip("<>") for x in link.split(",")
           if 'rel="next"' in x]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}

mains = [p for pref in PREFIXES for p in allp if p["handle"].startswith(pref)]
print(f"主品数: {len(mains)}")

# cs_inventory 总仓合计
cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()


def cap_num(opt):
    m = re.search(r"\d+(\.\d+)?", str(opt))
    return float(m.group(0)) if m else -1.0


# 1) 库存补齐（走 InventoryService 系统链路：本地记账+线上同步）
stocks = []
for p in mains:
    for v in p["variants"]:
        sku = v.get("sku") or ""
        csid = sku.split("_")[0] if sku else ""
        if not csid:
            continue
        cc.execute("SELECT COALESCE(SUM(quantity),0) FROM cs_inventory "
                   "WHERE cs_id=%s", (csid,))
        q = int(cc.fetchone()[0])
        stocks.append({"sku": sku, "available": q, "cs_id": csid,
                       "channel": "cs"})
        print(f"  {p['handle'][:40]:<40} {v['option1']:>9} {csid:<15} -> {q}")
cs.close()

r = InventoryService().apply_channel_stock(1, stocks)
print(f"补库存 RESULT checked={r.checked} updated={r.updated} "
      f"unchanged={r.unchanged} failed={r.failed}")

# 2) 容量从大到小重排 position
for p in mains:
    vs = sorted(p["variants"], key=lambda v: cap_num(v["option1"]),
                reverse=True)
    order = [v["option1"] for v in vs]
    cur = [v["option1"] for v in sorted(p["variants"],
                                        key=lambda x: x["position"])]
    if len(vs) < 2 or order == cur:
        print(f"= 顺序已对: {p['handle'][:50]} {order}")
        continue
    body = {"product": {"id": p["id"], "variants": [
        {"id": v["id"], "position": i + 1} for i, v in enumerate(vs)]}}
    rr = cl._client.put(f"products/{p['id']}.json", json=body, auth=cl._auth)
    rr.raise_for_status()
    print(f"↕ 重排: {p['handle'][:50]} {cur} -> {order}")
