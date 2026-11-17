# -*- coding: utf-8 -*-
"""生成 Google Shopping 全量 feed TSV (Cameron Sino 品牌 + GTIN + 规格)。"""
import csv
import html
import os
import re
import sys
import time

import pymysql
from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

BASE = "https://www.estrybattery.com"
CAT_MAP = {
    "Smart Phone": "Electronics > Communications > Telephony > "
                   "Mobile Phone Accessories > Mobile Phone Batteries",
    "Mobile Phone": "Electronics > Communications > Telephony > "
                    "Mobile Phone Accessories > Mobile Phone Batteries",
    "Camera": "Cameras & Optics > Camera Accessories > Camera Batteries",
    "Camcorder": "Cameras & Optics > Camera Accessories > Camera Batteries",
    "Laptop": "Electronics > Computers > Laptop Components > "
              "Laptop Batteries",
    "Notebook": "Electronics > Computers > Laptop Components > "
                "Laptop Batteries",
    "Power Tools": "Home & Garden > Tools > Power Tool Batteries",
    "Lawn Mowers": "Home & Garden > Lawn & Garden > "
                   "Outdoor Power Equipment Batteries",
}
FALLBACK_CAT = "Electronics > Electronics Accessories > Batteries"

cs = pymysql.connect(
    host=os.environ["CS_DB_HOST"], port=int(os.environ.get("CS_DB_PORT", 3306)),
    user=os.environ["CS_DB_USER"], password=os.environ["CS_DB_PASSWORD"],
    database=os.environ["CS_DB_NAME"], charset="utf8mb4")
cc = cs.cursor()
cc.execute("SELECT cs_id, category, capacity, voltage, battery_type "
           "FROM cs_product")
src = {a: (b, c, d, e) for a, b, c, d, e in cc.fetchall()}
cs.close()
print("源库规格:", len(src))

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "status": "active",
          "fields": "id,handle,title,body_html,images,variants"}
allp = []
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    allp += r.json()["products"]
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print("产品:", len(allp))

def desc_text(h):
    t = re.sub(r"<[^>]+>", " ", h or "")
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()[:4800]

COLS = ["id", "title", "description", "link", "image_link",
        "additional_image_link", "availability", "price", "brand", "gtin",
        "mpn", "condition", "google_product_category", "item_group_id",
        "product_weight", "product_detail:attribute_name:"
        "attribute_value:attribute_value", "custom_label_0"]
rows, skipped = [], {"无价": 0, "无图": 0, "无sku": 0}
for p in allp:
    imgs = [i["src"] for i in (p.get("images") or [])[:6]]
    if not imgs:
        skipped["无图"] += len(p["variants"])
        continue
    d = desc_text(p.get("body_html"))
    for v in p["variants"]:
        try:
            price = float(v.get("price") or 0)
        except Exception:
            price = 0
        if price <= 0:
            skipped["无价"] += 1
            continue
        sku = v.get("sku") or ""
        csid = sku.split("_")[0]
        if not csid.startswith("CS-"):
            skipped["无sku"] += 1
            continue
        cat, cap, volt, bt = src.get(csid, ("", "", "", ""))
        det = []
        if cap:
            det.append(("Capacity", cap))
        if volt:
            det.append(("Voltage", volt))
        if bt:
            det.append(("Battery Type", bt))
        gc = FALLBACK_CAT
        if cat:
            for k, m in CAT_MAP.items():
                if k.lower() in str(cat).lower():
                    gc = m
                    break
        title = p["title"]
        vt = v.get("title") or ""
        if vt and vt != "Default Title":
            title = f"{p['title']} - {vt}"
        rows.append({
            "id": f"estry_US_{v['id']}",
            "title": title[:148],
            "description": d or (p["title"])[:200],
            "link": f"{BASE}/products/{p['handle']}?variant={v['id']}",
            "image_link": imgs[0],
            "additional_image_link": ",".join(imgs[1:]),
            "availability": "in_stock",
            "price": f"{price:.2f} USD",
            "brand": "Cameron Sino",
            "gtin": v.get("barcode") or "",
            "mpn": csid,
            "condition": "new",
            "google_product_category": gc,
            "item_group_id": p["handle"][:50],
            "product_weight": f"{v.get('grams') or ''} g"
                              if v.get("grams") else "",
            "product_detail:attribute_name:attribute_value:"
            "attribute_value": ":".join(f"{k}:{val}:"
                              for k, val in det) if det else "",
            "custom_label_0": (str(cat) or "Battery")[:40],
        })

os.makedirs("/home/jason/shopify-admin/deploy/feed", exist_ok=True)
out = "/home/jason/shopify-admin/deploy/feed/estry_feed.tsv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS, delimiter="\t",
                       quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    w.writerows(rows)
print(f"\nfeed 行数: {len(rows)} -> {out}")
print("排除:", skipped)
print("GTIN 有码率:", sum(1 for r in rows if r['gtin'])*100//max(len(rows),1), "%")
