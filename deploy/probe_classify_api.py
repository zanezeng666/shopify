# -*- coding: utf-8 -*-
"""Shopify API 侧探测（jason venv）：metafield definitions / collections / 样例。"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")

from sqlalchemy import text


def main() -> None:
    from shopify_admin.services.stores import StoreService
    from shopify_admin.core.database import session_scope
    c = StoreService().get_client(1)

    print("== D1. metafield definitions (PRODUCT) ==")
    r = c.graphql("{ metafieldDefinitions(first: 50, ownerType: PRODUCT)"
                  "{ edges { node { namespace key name type { name } } } } }")
    defs = (r.get("data", {}) or {}).get("metafieldDefinitions", {}).get("edges", [])
    if not defs:
        print(f"  无定义 / resp={str(r)[:200]}")
    for e in defs:
        n = e["node"]
        tn = ((n.get("type") or {}).get("name") or "?") if isinstance(n.get("type"), dict) else n.get("type")
        print(f"  {n['namespace']}.{n['key']:28} type={str(tn):18} {n['name']}")

    print("\n== D2. collections 实况 count ==")
    for kind in ("custom_collections", "smart_collections"):
        try:
            n = c.request("GET", f"{kind}/count.json").get("count")
            print(f"  {kind} = {n}")
        except Exception as ex:  # noqa: BLE001
            print(f"  {kind} ERR {ex}")

    print("\n== D3. 样例产品 metafields（首个 active CS- 产品）==")
    with session_scope() as s:
        row = s.execute(text(
            "SELECT v.shopify_product_id, p.title FROM products p "
            "JOIN product_variants v ON v.product_id = p.id AND v.store_id = 1 "
            "WHERE p.store_id=1 AND p.status='active' AND v.sku LIKE 'CS-%%' "
            "LIMIT 1")).one()
    spid, title = row
    print(f"  产品: {spid} {title[:60]}")
    mfs = c.request("GET", f"products/{spid}/metafields.json",
                    params={"limit": 20}).get("metafields", [])
    if not mfs:
        print("  metafields: 空")
    for m in mfs:
        print(f"  {m['namespace']}.{m['key']:26} type={m['type']:20} "
              f"value={str(m['value'])[:40]!r}")

    print("\nAPI-PROBE-OK")


if __name__ == "__main__":
    main()
