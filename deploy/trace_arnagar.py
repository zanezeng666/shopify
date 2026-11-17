# -*- coding: utf-8 -*-
"""追 Arnagar/Blaupunkt 页的分组落点：sku、源库 pn/fm/cap。"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,title,variants", "status": "active"}
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

KW = ("arnagar", "blaupunkt", "bralko")
seen = 0
for p in allp:
    h = p["handle"].lower()
    if not any(k in h for k in KW):
        continue
    seen += 1
    if seen > 6:
        break
    v = p["variants"][0] if p.get("variants") else {}
    sku = v.get("sku") or ""
    csid = sku.split("_")[0] if sku else "(no sku)"
    cc.execute("SELECT part_no, fit_model, capacity FROM cs_product "
               "WHERE cs_id=%s", (csid,))
    row = cc.fetchone()
    print(f"{h[:55]}")
    print(f"   sku={sku[:40]} -> src={row}")
cs.close()
