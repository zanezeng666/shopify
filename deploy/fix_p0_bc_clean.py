# -*- coding: utf-8 -*-
"""P0-2a 清尾：active 商品条码/品牌残留治理（可逆：先 dump 存档）
1) dump 全部带码 active 变体 + 非 Estry vendor active 商品 → backup 文件
2) 13位 EAN(Cameron Sino 残留) → 清空 barcode（转 Estry+MPN 模式）
3) 12位 UPC → 校验位合法保留，非法清空
4) vendor != Estry 的 active 商品 → vendor=Estry
"""
import json
import time

from dotenv import load_dotenv

load_dotenv("/home/jason/shopify-admin/.env")
from shopify_admin.services.stores.service import StoreService  # noqa

client = StoreService().get_client(1)
BAK = "/home/jason/shopify-admin/deploy/backup_p0_bc_active.json"


def upc_ok(code):
    if len(code) != 12 or not code.isdigit():
        return False
    d = [int(c) for c in code]
    return (10 - ((d[0] + d[2] + d[4] + d[6] + d[8] + d[10]) * 3
                  + d[1] + d[3] + d[5] + d[7] + d[9]) % 10) % 10 == d[11]


bc_variants = []   # (variant_id, product_id, sku, barcode, vendor)
vendor_fix = []    # (product_id, old_vendor)
since = 0
while True:
    batch = client.request("GET", "products.json", params={
        "limit": 250, "since_id": since, "status": "active"}).get(
            "products", [])
    if not batch:
        break
    for p in batch:
        if (p.get("vendor") or "") != "Estry":
            vendor_fix.append((p["id"], p.get("vendor")))
        for v in p.get("variants", []):
            bc = (v.get("barcode") or "").strip()
            if bc:
                bc_variants.append((v["id"], p["id"], v.get("sku"), bc,
                                    p.get("vendor")))
    since = batch[-1]["id"]
    time.sleep(0.45)

json.dump({"bc_variants": bc_variants, "vendor_fix": vendor_fix},
          open(BAK, "w"), ensure_ascii=False, indent=1)
print(f"dump {len(bc_variants)} 带码变体 + {len(vendor_fix)} 个 vendor 修正"
      f" → {BAK}")

to_clear = []
kept_upc = []
for vid, pid, sku, bc, vd in bc_variants:
    if len(bc) == 13:
        to_clear.append((vid, pid, sku, bc))
    elif len(bc) == 12 and upc_ok(bc):
        kept_upc.append((vid, sku, bc))
    else:
        to_clear.append((vid, pid, sku, bc))
print(f"计划清空 {len(to_clear)} 个（EAN13/非法UPC），"
      f"保留合法 UPC {len(kept_upc)} 个：")
for vid, sku, bc in kept_upc[:10]:
    print(f"  KEEP {sku} {bc}")

fail = 0
for vid, pid, sku, bc in to_clear:
    try:
        client.request("PUT", f"variants/{vid}.json",
                       json_body={"variant": {"id": vid, "barcode": ""}})
    except Exception as ex:  # noqa: BLE001
        fail += 1
        print(f"  CLEAR FAIL {vid} {sku}: {str(ex)[:100]}")
    time.sleep(0.45)
print(f"清空完成，失败 {fail}")

fail = 0
for pid, old in vendor_fix:
    try:
        client.request("PUT", f"products/{pid}.json",
                       json_body={"product": {"id": pid, "vendor": "Estry"}})
        print(f"  VENDOR {pid}: {old} -> Estry")
    except Exception as ex:  # noqa: BLE001
        fail += 1
        print(f"  VENDOR FAIL {pid}: {str(ex)[:100]}")
    time.sleep(0.45)
print(f"vendor 修正完成，失败 {fail}")
client.close()
