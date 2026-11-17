# -*- coding: utf-8 -*-
"""自动分类+元字段：只读探测（2026-11-03）。

A. cs_inventory.location 值分布 → 美仓标识确认
B. 美仓有库存电池产品：category 分布 + metafield 候选字段填充率
C. 镜像库：product_type 分布 / collections / metafields 现状
D. Shopify 实况：metafield definitions + collections count + 样例产品 metafields
"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")

from sqlalchemy import text


def main() -> None:
    # ------------------------------------------------------------------
    # A. 库位分布
    # ------------------------------------------------------------------
    from bmai.core.database import cs_engine
    with cs_engine.connect() as c:
        print("== A. cs_inventory.location 分布 ==")
        for loc, n, qty in c.execute(text(
            "SELECT location, COUNT(DISTINCT cs_id), SUM(quantity) FROM cs_inventory "
            "GROUP BY location ORDER BY SUM(quantity) DESC")).all():
            print(f"  {loc!r:30} cs_ids={n:6}  qty={qty}")

        # B. 美仓（location 含 US/USA，以 A 实况为准，先宽匹配看数量级）
        print("\n== B. 美仓有库存电池（CS- 前缀, status=1）==")
        q = text("""
            SELECT p.category,
                   COUNT(*) AS n,
                   SUM(p.capacity <> '')      AS has_cap,
                   SUM(p.voltage <> '')       AS has_v,
                   SUM(p.battery_type <> '')  AS has_bt,
                   SUM(p.fit_model <> '')     AS has_fit,
                   SUM(p.part_no <> '')       AS has_pn,
                   SUM(p.dimension <> '')     AS has_dim,
                   SUM(p.net_weight_g > 0)    AS has_wt,
                   SUM(p.wh_value IS NOT NULL AND p.wh_value > 0) AS has_wh
            FROM cs_product p
            WHERE p.cs_id LIKE 'CS-%%'
              AND p.status = 1
              AND p.cs_id IN (
                  SELECT cs_id FROM cs_inventory
                  WHERE quantity > 0 AND location LIKE '%%US%%')
            GROUP BY p.category ORDER BY n DESC
        """)
        rows = c.execute(q).all()
        skip = {"Mobile, SmartPhone", "Notebook, Laptop", "Camera"}
        tot = sum(r[1] for r in rows)
        skp = sum(r[1] for r in rows if r[0] in skip)
        print(f"  类目数={len(rows)}  美仓产品记录={tot}  其中跳过三类={skp}  待分类={tot - skp}")
        for cat, n, cap, v, bt, fit, pn, dim, wt, wh in rows:
            flag = "  [SKIP]" if cat in skip else ""
            print(f"  {cat!r:34} n={n:5}  cap={cap:5} volt={v:5} chem={bt:5} "
                  f"fit={fit:5} pno={pn:5} dim={dim:5} wt={wt:5} wh={wh:5}{flag}")

    # ------------------------------------------------------------------
    # C. 镜像库现状
    # ------------------------------------------------------------------
    from shopify_admin.core.database import session_scope
    with session_scope() as s:
        print("\n== C1. products.product_type 分布（镜像, store=1）==")
        rows = s.execute(text(
            "SELECT product_type, status, COUNT(*) FROM products WHERE store_id=1 "
            "GROUP BY product_type, status ORDER BY COUNT(*) DESC LIMIT 45")).all()
        for pt, st, n in rows:
            print(f"  {pt!r:38} {st:9} {n}")
        n_pt = s.execute(text(
            "SELECT COUNT(DISTINCT product_type) FROM products WHERE store_id=1")).scalar()
        n_all = s.execute(text(
            "SELECT COUNT(*) FROM products WHERE store_id=1")).scalar()
        print(f"  ... 总产品={n_all}  product_type 去重={n_pt}")

        print("\n== C2. collections / 关联 / metafields（镜像）==")
        for label, sql in [
            ("collections 总数", "SELECT COUNT(*), SUM(is_smart) FROM collections WHERE store_id=1"),
            ("collections 样例", "SELECT title, is_smart, published_at FROM collections "
             "WHERE store_id=1 ORDER BY id DESC LIMIT 12"),
            ("product_collections", "SELECT COUNT(*) FROM product_collections"),
            ("metafields", "SELECT owner_resource, namespace, `key`, COUNT(*) FROM metafields "
             "WHERE store_id=1 GROUP BY owner_resource, namespace, `key` LIMIT 15"),
        ]:
            print(f"  -- {label} --")
            try:
                for r in s.execute(text(sql)).all():
                    print(f"  {tuple(r)}")
            except Exception as e:  # noqa: BLE001
                print(f"  ERR {e}")

    # ------------------------------------------------------------------
    # D. Shopify 实况
    # ------------------------------------------------------------------
    from shopify_admin.services.store import StoreService
    c = StoreService().get_client(1)
    print("\n== D1. metafield definitions (PRODUCT) ==")
    r = c.graphql("{ metafieldDefinitions(first: 50, ownerType: PRODUCT)"
                  "{ edges { node { namespace key name type } } } }")
    defs = (r.get("data", {}).get("metafieldDefinitions", {}) or {}).get("edges", [])
    if not defs:
        print(f"  无定义 / resp={str(r)[:200]}")
    for e in defs:
        n = e["node"]
        print(f"  {n['namespace']}.{n['key']:28} type={n['type']:18} {n['name']}")

    print("\n== D2. collections 实况 count ==")
    for kind in ("custom_collections", "smart_collections"):
        try:
            n = c.request("GET", f"{kind}/count.json").get("count")
            print(f"  {kind} = {n}")
        except Exception as e:  # noqa: BLE001
            print(f"  {kind} ERR {e}")

    print("\n== D3. 样例产品 metafields（首个 active CS- 产品）==")
    with session_scope() as s:
        spid, title = s.execute(text(
            "SELECT v.shopify_product_id, p.title FROM products p "
            "JOIN product_variants v ON v.product_id = p.id AND v.store_id = 1 "
            "WHERE p.store_id=1 AND p.status='active' AND v.sku LIKE 'CS-%%' "
            "LIMIT 1")).one()
    print(f"  产品: {spid} {title[:60]}")
    mfs = c.request("GET", f"products/{spid}/metafields.json",
                    params={"limit": 20}).get("metafields", [])
    if not mfs:
        print("  metafields: 空（店铺产品未使用自定义字段）")
    for m in mfs:
        print(f"  {m['namespace']}.{m['key']:26} type={m['type']:20} "
              f"value={str(m['value'])[:40]!r}")

    print("\nPROBE-OK")


if __name__ == "__main__":
    main()
