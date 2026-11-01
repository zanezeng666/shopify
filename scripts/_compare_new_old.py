# -*- coding: utf-8 -*-
"""对比新建的 CS-TVR500VX draft 产品与店铺存量老产品（逐字段，只读）。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import session_scope
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.client import ShopifyClient
from shopify_admin.platforms.shopify.rest import ShopifyRest

svc = StoreService()
client = svc.get_client(1)
rest = ShopifyRest(client)

# 店铺镜像里 CS-TVR500VX 相关变体（老 3 品牌 + 新 21 品牌）
with session_scope() as s:
    rows = s.execute(text(
        "SELECT v.shopify_product_id, v.sku FROM product_variants v "
        "WHERE v.sku LIKE 'CS-TVR500VX%' ORDER BY v.id")).all()
by_pid = {}
for pid, sku in rows:
    by_pid.setdefault(pid, []).append(sku)
print(f"本地镜像 CS-TVR500VX 产品数: {len(by_pid)}")

out = []
for pid, skus in by_pid.items():
    try:
        p = client.request("GET", f"products/{pid}.json")["product"]
    except Exception as e:  # noqa: BLE001
        out.append({"pid": pid, "skus": skus, "error": str(e)})
        continue
    v0 = (p.get("variants") or [{}])[0]
    out.append({
        "pid": pid,
        "skus": sorted(skus),
        "status": p.get("status"),
        "title": p.get("title"),
        "handle": p.get("handle"),
        "vendor": p.get("vendor"),
        "product_type": p.get("product_type"),
        "tags": p.get("tags"),
        "body_chars": len(p.get("body_html") or ""),
        "body_head": (p.get("body_html") or "")[:80],
        "options": [o.get("name") for o in p.get("options") or []],
        "v": {"sku": v0.get("sku"), "price": v0.get("price"), "grams": v0.get("grams"),
              "barcode": v0.get("barcode"), "inv": v0.get("inventory_management"),
              "option": v0.get("option1")},
    })

with open(Path(__file__).parent / "_compare_out.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print(f"已写 {len(out)} 个产品到 scripts/_compare_out.json")
# 摘要打印（draft=新建 / active=存量）
for o in out:
    if "error" in o:
        print(o["pid"], "ERROR", o["error"][:60]); continue
    print(f"[{o['status']}] {o['handle']} | title={o['title']!r}")
    print(f"    v.sku={o['v']['sku']} price={o['v']['price']} g={o['v']['grams']} "
          f"bc={o['v']['barcode']} inv={o['v']['inv']} type={o['vendor']!r}/{o['product_type']!r} "
          f"tags={o['tags']!r}")
