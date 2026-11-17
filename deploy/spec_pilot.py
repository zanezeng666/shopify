# -*- coding: utf-8 -*-
"""试点: zebra 主品插入规格书表格(同站内风格), 保留原描述。"""
import os
import re
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
cl = ShopifyRest(StoreService().get_client(1)).client

params = {"limit": 250, "created_at_min": "2026-10-30T00:00:00Z",
          "fields": "id,handle,body_html,variants", "status": "active"}
hit = None
while not hit:
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    for x in r.json()["products"]:
        if x["handle"].startswith("battery-for-zebra-zr138"):
            hit = x
            break
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
cs.close()

rows, gen = [], {}
for v in sorted(hit["variants"], key=lambda x: x["position"] or 9):
    csid = (v.get("sku") or "").split("_")[0]
    if not csid.startswith("CS-"):
        continue
    cc2 = pymysql.connect(
        host=os.environ["CS_DB_HOST"],
        port=int(os.environ.get("CS_DB_PORT", 3306)),
        user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
        database=os.environ["CS_DB_NAME"], charset="utf8mb4")
    c3 = cc2.cursor()
    c3.execute(
        "SELECT category,brand,part_no,dimension,battery_type,capacity,"
        "net_weight_g,voltage,bar_code FROM cs_product WHERE cs_id=%s",
        (csid,))
    f = c3.fetchone()
    cc2.close()
    if not f:
        continue
    (cat, br, pn, dim, bt, cap, wg, volt, bc) = f
    gen = {"category": cat, "brand": br, "battery_type": bt}
    try:
        wh = float(volt.rstrip("V")) * float(cap.rstrip("mAh")) / 1000
        whs = f"{wh:.1f}Wh"
    except Exception:
        whs = ""
    rows.append([csid, cap, volt, whs, dim, f"{int(wg)}g" if wg else "",
                 pn.split(",")[0].strip()])

T = ('border-collapse:collapse;width:100%;margin:0 0 18px;'
     'border:1px solid #D9E2EC;border-radius:8px;overflow:hidden;'
     'font-size:13px;color:#2A3B4F;')
TH = ('background:#F4F6F8;color:#1B2A41;font-weight:600;'
      'padding:9px 12px;text-align:left;border-bottom:1px solid #D9E2EC;')
TD = 'padding:8px 12px;border-bottom:1px solid #E5EBF1;vertical-align:top;'
cols = ["Model", "Capacity", "Voltage", "Energy", "Dimensions", "Weight",
        "OEM Part No."]
h = (f'<div style="margin:0 0 8px;font-size:16px;font-weight:700;'
     f'color:#1B2A41;">Battery Specifications</div>'
     f'<table style="{T}"><tr>'
     + "".join(f'<th style="{TH}">{c}</th>' for c in cols) + "</tr>")
for row in rows:
    h += "<tr>" + "".join(f'<td style="{TD}">{x}</td>' for x in row) + "</tr>"
h += "</table>"
if gen.get("category"):
    h += (f'<div style="font-size:13px;color:#5A6B7F;margin:0 0 18px;">'
          f'Category: {gen["category"]} &nbsp;|&nbsp; '
          f'Fits {gen["brand"]} devices &nbsp;|&nbsp; '
          f'Chemistry: {gen.get("battery_type", "")}</div>')

body = hit["body_html"] or ""
if "Battery Specifications</div>" in body:
    print("已插过, 跳过")
else:
    i = body.find("</div>")
    pos = (i + 6) if i > -1 else 0
    nb = body[:pos] + h + body[pos:]
    r = cl._client.put(f"products/{hit['id']}.json", auth=cl._auth,
                       json={"product": {"id": hit["id"], "body_html": nb}})
    r.raise_for_status()
    print("已插入规格表, 品:", hit["handle"])
    print("预览: https://www.estrybattery.com/products/" + hit["handle"])
