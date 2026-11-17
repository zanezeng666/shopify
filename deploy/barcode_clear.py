# -*- coding: utf-8 -*-
"""双保险存档后清空全店 barcode(止血: 切换 Estry+MPN 模式)。幂等可重跑。

存档双保险:
  1. 全量 variant_id->barcode dump 到 deploy/backup/ (含 product_id/sku)
  2. 源库 cs_product.bar_code 映射永久保留(不触碰)
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client

BK = Path("/home/jason/shopify-admin/deploy/backup/barcode_backup_20261108.jsonl")
BK.parent.mkdir(parents=True, exist_ok=True)
dumped = BK.exists()

# ---- 1) 分页拉取 active 变体, dump 存档 + 收集待清清单 ----
params = {"limit": 250, "status": "active", "fields": "id,variants"}
have_bc = []
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth,
                       timeout=60)
    r.raise_for_status()
    for p in r.json()["products"]:
        for v in p["variants"]:
            bc = v.get("barcode") or ""
            if bc:
                have_bc.append((v["id"], v.get("sku", ""), bc))
                if not dumped:
                    with open(BK, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "variant_id": v["id"],
                            "product_id": p["id"],
                            "sku": v.get("sku", ""),
                            "barcode": bc}) + "\n")
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,variants"}

size = BK.stat().st_size if BK.exists() else 0
print(f"待清 barcode 变体: {len(have_bc)} | 存档 {BK.name} "
      f"({size // 1024}KB, {'已有' if dumped else '本次新建'})", flush=True)

# ---- 2) 逐个清空 (0.45s 间隔, 重试3次) ----
ok = fail = 0
for i, (vid, sku, bc) in enumerate(have_bc, 1):
    for attempt in range(3):
        try:
            time.sleep(0.45)
            r2 = cl._client.put(f"variants/{vid}.json", auth=cl._auth,
                                json={"variant": {"id": vid, "barcode": ""}},
                                timeout=30)
            r2.raise_for_status()
            ok += 1
            break
        except Exception as ex:
            if attempt == 2:
                fail += 1
                print(f"FAIL vid={vid} sku={sku} bc={bc} {str(ex)[:90]}",
                      flush=True)
            else:
                time.sleep(2 ** attempt)
    if i % 500 == 0:
        print(f"进度 {i}/{len(have_bc)} ok={ok} fail={fail}", flush=True)

print(f"清码完成: ok={ok} fail={fail}", flush=True)
