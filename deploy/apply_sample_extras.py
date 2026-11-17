# -*- coding: utf-8 -*-
"""样例产品应用 v2.2 增项：绿线新版 body / 选项名 Capacity / seo.description / 图片 alt。

用法: python apply_sample_extras.py [product_id]   # 默认 15484753215732
"""
import sys
import re
import json

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.products.sync_shopify import CsShopifySyncService as S
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

PID = next((int(a) for a in sys.argv[1:] if a.isdigit()), 15484753215732)
CS_RE = re.compile(r"^CS-([A-Z0-9]+)_", re.I)

svc = S()
catalog = svc.load_cs_catalog()
client = StoreService().get_client(1)
rest = ShopifyRest(client)

p = rest.client.request("GET", f"products/{PID}.json", params={
    "fields": "id,title,options,images,variants"}).get("product", {})
if not p:
    print("FATAL: product not found:", PID); sys.exit(1)

sku = p["variants"][0]["sku"]
m = CS_RE.match(sku)
csid = ("CS-" + m.group(1)).upper()
brand_seg = sku.split("_")[1].lower() if sku.count("_") >= 2 else ""
rows = [(str(bl).lower(), r) for (c, bl), r in catalog.items() if str(c).upper() == csid]
if not rows:
    print("FATAL: no cs source for", csid); sys.exit(1)
row = next((r for bl, r in rows if bl == brand_seg), rows[0][1])

body = S._build_body_html(row)
img_payload = [{"id": im["id"],
                "alt": p["title"] if n == 0 else f"{p['title']} - {n + 1}"}
               for n, im in enumerate(p.get("images", []))]
rest.update_product(PID, {
    "id": PID, "body_html": body,
    "options": [{"name": "Capacity"}],
    "images": img_payload,
})

# REST 产品更新不新建 metafield，走独立端点（存在则 PUT，否则 POST）
seo_val = S._entity_text(row)[:155]
mfs = rest.client.request(
    "GET", f"products/{PID}/metafields.json",
    params={"namespace": "seo"}).get("metafields", [])
cur_mf = next((x for x in mfs if x["key"] == "description"), None)
if cur_mf:
    rest.client.request(
        "PUT", f"products/{PID}/metafields/{cur_mf['id']}.json",
        json_body={"metafield": {"id": cur_mf["id"], "value": seo_val,
                                 "type": "single_line_text_field"}})
else:
    rest.client.request(
        "POST", f"products/{PID}/metafields.json",
        json_body={"metafield": {"namespace": "seo", "key": "description",
                                 "value": seo_val,
                                 "type": "single_line_text_field"}})

chk = rest.client.request("GET", f"products/{PID}.json", params={
    "fields": "options,images,body_html"}).get("product", {})
mfs = rest.client.request("GET", f"products/{PID}/metafields.json",
                          params={"namespace": "seo"}).get("metafields", [])
seo_val_now = next((x["value"] for x in mfs if x["key"] == "description"), None)
print(json.dumps({
    "id": PID,
    "options": [o["name"] for o in chk["options"]],
    "seo_description": seo_val_now,
    "alts": [i.get("alt") for i in chk.get("images", [])],
    "green_gone": "#00A651" not in (chk.get("body_html") or ""),
    "navy_underline": "border-bottom:2px solid #1B2A41" in (chk.get("body_html") or ""),
}, ensure_ascii=False, indent=1))
client.close()
