# -*- coding: utf-8 -*-
"""缺图8个补图复活：SKU->cs_id->图库探测->Shopify挂图->恢复active。"""
import json
import re
import sys

import httpx
from sqlalchemy import text

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.core.database import get_engine  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

CS_IMG_BASE = "https://cameronsino.co/images"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/126.0 Safari/537.36"}

recs = json.load(open("/home/jason/shopify-admin/deploy/mc_issues_20261116.json"))
seen, pids = set(), []
for r in recs:
    for i in r["issues"]:
        if i["code"] == "item_missing_required_attribute" and r["offerId"] not in seen:
            seen.add(r["offerId"])
            pids.append(r["offerId"].split("_")[2])

eng = get_engine()
cl = ShopifyRest(StoreService().get_client(1)).client

with httpx.Client(timeout=15, headers=UA) as hc:
    def head(u):
        return hc.head(u).status_code == 200

    for pid in pids:
        with eng.connect() as c:
            row = c.execute(text(
                "SELECT sku FROM product_variants "
                "WHERE shopify_product_id=:i LIMIT 1"),
                {"i": int(pid)}).first()
        if not row or not row[0]:
            print(f"{pid}: 无SKU，保持 draft")
            continue
        m = re.match(r"^(CS-[A-Za-z0-9]+)", row[0])
        if not m:
            print(f"{pid}: SKU 非 CS 格式({row[0][:24]})，保持 draft")
            continue
        cs_id = m.group(1)
        urls = []
        for n in range(1, 13):
            u = f"{CS_IMG_BASE}/{cs_id}-{n}.jpg"
            try:
                ok = head(u)
            except Exception:  # noqa
                ok = False
            if not ok:
                break
            urls.append(u)
        if not urls:
            print(f"{pid}: {cs_id} 图库无图，保持 draft")
            continue
        for u in urls:
            try:
                cl.request("POST", f"products/{pid}/images.json",
                           json_body={"image": {"src": u}})
            except Exception as e:  # noqa
                print(f"  挂图失败 {u[-28:]}: {e}")
                break
        cl.request("PUT", f"products/{pid}.json", json_body={
            "product": {"id": int(pid), "status": "active"}})
        print(f"{pid}: {cs_id} 挂图{len(urls)}张 + 恢复 active")
