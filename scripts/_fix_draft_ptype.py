# -*- coding: utf-8 -*-
"""给已创建的 21 个 CS-TVR500VX draft 产品补 product_type（存量规则对齐）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import session_scope
from shopify_admin.services.stores.service import StoreService

svc = StoreService()
client = svc.get_client(1)

with session_scope() as s:
    rows = s.execute(text(
        "SELECT v.shopify_product_id, v.sku FROM product_variants v "
        "WHERE v.sku LIKE 'CS-TVR500VX%' AND v.shopify_product_id > 10000000000000"
    )).all()

print("draft 产品数:", len(rows))
ok = fail = 0
for pid, sku in rows:
    try:
        r = client.request("PUT", f"products/{pid}.json",
                           json_body={"product": {"id": pid,
                                                  "product_type": "Vacuum Battery"}})
        ok += 1
    except Exception as e:  # noqa: BLE001
        fail += 1
        print("FAIL", pid, str(e)[:80])
print(f"更新 product_type: ok={ok} fail={fail}")
