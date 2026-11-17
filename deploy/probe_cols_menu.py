# -*- coding: utf-8 -*-
"""收官探测：集合匹配真实计数 + 导航菜单现状（只读）。"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    print("== E1. smart collection 真实匹配计数（GraphQL by handle）==")
    q = """
    {
      c1: collectionByHandle(handle: "vacuum-battery") { title productsCount { count } }
      c2: collectionByHandle(handle: "cordless-phone-battery") { title productsCount { count } }
      c3: collectionByHandle(handle: "two-way-radio-battery") { title productsCount { count } }
      c4: collectionByHandle(handle: "wireless-headset-battery") { title productsCount { count } }
      c5: collectionByHandle(handle: "camera-battery") { title productsCount { count } }
    }"""
    r = c.graphql(q)
    data = r.get("data", {}) or {}
    for i in range(1, 6):
        n = data.get(f"c{i}")
        if n:
            print(f"  {n['title'][:36]!r:40} productsCount={n['productsCount']['count']}")

    print("\n== E2. 导航菜单（GraphQL menu）==")
    q2 = '{ m1: menu(handle: "main-menu") { title items { title url } } '\
         'm2: menu(handle: "main-menu-1") { title items { title url } } '\
         'm3: menu(handle: "footer") { title items { title url } } }'
    r2 = c.graphql(q2)
    mdata = r2.get("data", {}) or {}
    for k in ("m1", "m2", "m3"):
        m = mdata.get(k)
        if m:
            print(f"  -- {k}: {m['title']!r} --")
            for it in m.get("items", []):
                print(f"    {it['title']!r:28} -> {it.get('url','')[:62]}")

    print("\n== E3. metafieldsSet 权限冒烟（dry：查 1 个美仓产品的定位链）==")
    from sqlalchemy import text
    from shopify_admin.core.database import session_scope
    with session_scope() as s:
        row = s.execute(text("""
            SELECT v.shopify_product_id, v.sku, p.title FROM products p
            JOIN product_variants v ON v.product_id=p.id AND v.store_id=1
            WHERE p.store_id=1 AND p.status='active' AND v.sku LIKE 'CS-%%'
              AND p.product_type='Vacuum Battery' LIMIT 3""")).all()
        for spid, sku, title in row:
            print(f"  {spid}  sku={sku[:40]!r}  {title[:50]}")

    print("\nFINAL-PROBE-OK")


if __name__ == "__main__":
    main()
