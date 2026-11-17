"""按当前模板规则重刷近期生成的产品。

用法: python refresh_body.py [dry] [product_id]   # 默认实跑；带数字只刷该产品
范围: Shopify created_at >= 2026-10-30（我们首次建品窗口）
逻辑: SKU 解析 cs_id → 新规则重建 body → 与线上一致则跳过，不同才 PUT
"""
import sys, re, json

sys.path.insert(0, "/home/jason/shopify-admin/src")
_args = sys.argv[1:]
DRY = "dry" in _args
ONLY_PID = next((int(a) for a in _args if a.isdigit()), None)

from shopify_admin.services.products.sync_shopify import CsShopifySyncService as S
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

CS_RE = re.compile(r"^CS-([A-Z0-9]+)_", re.I)

svc = S()
catalog = svc.load_cs_catalog()
by_csid = {}
for (csid, bl), row in catalog.items():
    by_csid.setdefault(str(csid).upper(), []).append((str(bl).lower(), row))

client = StoreService().get_client(1)
rest = ShopifyRest(client)

if ONLY_PID:
    prods = [rest.client.request("GET", f"products/{ONLY_PID}.json", params={
        "fields": "id,handle,body_html,created_at,variants",
    }).get("product", {})]
    if not prods[0]:
        print("FATAL: product not found:", ONLY_PID); sys.exit(1)
else:
    prods = rest.client.request("GET", "products.json", params={
        "created_at_min": "2026-10-30T00:00:00Z", "limit": 250,
        "fields": "id,handle,body_html,created_at,variants",
    }).get("products", [])
    if len(prods) >= 250:
        print("FATAL: >=250 products, need cursor pagination"); sys.exit(1)

same, no_src, updated, errors, changed = [], [], 0, [], []
for p in prods:
    if ONLY_PID and p["id"] != ONLY_PID:
        continue
    sku = (p.get("variants") or [{}])[0].get("sku") or ""
    m = CS_RE.match(sku)
    rows = by_csid.get(("CS-" + m.group(1)).upper()) if m else None
    if not rows:
        no_src.append({"id": p["id"], "sku": sku[:40]})
        continue
    brand_seg = (sku.split("_")[1] if sku.count("_") >= 2 else "").lower()
    row = next((r for bl, r in rows if bl == brand_seg), rows[0][1])
    new_body = S._build_body_html(row)
    if (p.get("body_html") or "") == new_body:
        same.append(p["id"])
        continue
    changed.append({"id": p["id"], "handle": p["handle"]})
    if not DRY:
        try:
            rest.update_product(p["id"], {"id": p["id"], "body_html": new_body})
            updated += 1
        except Exception as e:
            errors.append(f"{p['id']}: {str(e)[:150]}")

client.close()
print(json.dumps({
    "mode": "DRY" if DRY else "APPLY", "pulled": len(prods),
    "need_change": len(changed), "already_conform": len(same),
    "no_cs_source": len(no_src), "updated": updated,
    "errors": errors, "sample_changed": changed[:6],
    "sample_no_source": no_src[:3],
}, ensure_ascii=False, indent=1))
