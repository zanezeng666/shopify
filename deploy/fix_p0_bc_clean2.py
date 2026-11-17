# -*- coding: utf-8 -*-
"""P0-2a 补清：backup 中剩余 35 个 12 位(732416x CS段, 前导零丢失的EAN) 清空"""
import json
import time

from dotenv import load_dotenv  # noqa: E402

BAK = "/home/jason/shopify-admin/deploy/backup_p0_bc_active.json"
data = json.load(open(BAK))
targets = [(vid, sku, bc) for vid, pid, sku, bc, vd in data["bc_variants"]
           if len(bc) == 12]
print(f"补清 {len(targets)} 个 12 位 CS-EAN 残留")
fail = 0
from dotenv import load_dotenv  # noqa: E402

load_dotenv("/home/jason/shopify-admin/.env")
from shopify_admin.services.stores.service import StoreService  # noqa

client = StoreService().get_client(1)
for vid, sku, bc in targets:
    try:
        client.request("PUT", f"variants/{vid}.json",
                       json_body={"variant": {"id": vid, "barcode": ""}})
    except Exception as ex:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {vid} {sku}: {str(ex)[:100]}")
    time.sleep(0.45)
print(f"补清完成，失败 {fail}。backup 保留在 {BAK} 可随时回滚")
client.close()
