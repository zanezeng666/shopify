# -*- coding: utf-8 -*-
"""21 个 draft 产品更新：body_html（新规格表模板）+ option1（容量）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import session_scope
from shopify_admin.services.stores.service import StoreService
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

svc = StoreService()
client = svc.get_client(1)
sync = CsShopifySyncService()
catalog = sync.load_cs_catalog()          # key=(cs_id, brand.lower())

with session_scope() as s:
    rows = s.execute(text(
        "SELECT shopify_product_id, sku FROM product_variants "
        "WHERE sku LIKE 'CS-TVR500VX%' ORDER BY id")).all()

ok = fail = 0
for pid, sku in rows:
    if pid < 10000000000000:              # 老 active 不动
        continue
    parts = sku.split("_")
    cs_id, brand_seg = parts[0], parts[1]
    cs_row = catalog.get((cs_id, brand_seg.lower()))
    if not cs_row:
        print(f"[{pid}] SKIP 无 CS 记录: {sku}")
        continue
    try:
        p = client.request("GET", f"products/{pid}.json",
                           params={"fields": "id,variants,options"})["product"]
        vid = p["variants"][0]["id"]
        option1 = (cs_row.get("capacity") or "").strip() or "Default Title"
        r = client.request("PUT", f"products/{pid}.json", json_body={"product": {
            "id": pid,
            "body_html": sync._build_body_html(cs_row),   # noqa: SLF001
            "variants": [{"id": vid, "option1": option1}],
        }})["product"]
        opts = r.get("options") or []
        print(f"[{pid}] OK  {sku}  option1={option1!r}  options={[(o.get('name'), o.get('values')) for o in opts]}")
        ok += 1
    except Exception as e:  # noqa: BLE001
        print(f"[{pid}] FAIL {sku}: {str(e)[:120]}")
        fail += 1

print(f"\ndone: ok={ok} fail={fail}")
