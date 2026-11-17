# -*- coding: utf-8 -*-
"""自动分类数据探测（root + bmai venv，纯 CDB 只读）。

读 /data/bmai/.env 的 DB_* → 直连 cs_new / shopify_new。
A. cs_inventory.location 分布
B. 美仓有库存电池：category 分布 + 字段填充率
C. shopify_new 镜像：product_type / collections / metafields
"""
import re
import sys
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text


def load_env() -> dict:
    env = {}
    with open("/data/bmai/.env", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(DB_[A-Z_]+)\s*=\s*(.+)$", line.strip())
            if m:
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return env


def main() -> None:
    e = load_env()
    user = e.get("DB_USER") or e.get("DB_USERNAME") or "root"
    pwd = quote_plus(e.get("DB_PASSWORD", ""))
    host = e.get("DB_HOST")
    url = (f"mysql+pymysql://{user}:{pwd}@{host}:{e.get('DB_PORT', '3306')}"
           f"/cs_new?charset=utf8mb4")
    cs = create_engine(url, pool_pre_ping=True)
    shop = create_engine(url.replace("/cs_new?", "/shopify_new?"), pool_pre_ping=True)

    with cs.connect() as c:
        print("== A. cs_inventory.location 分布 ==")
        for loc, n, qty in c.execute(text(
            "SELECT location, COUNT(DISTINCT cs_id), SUM(quantity) FROM cs_inventory "
            "GROUP BY location ORDER BY SUM(quantity) DESC")).all():
            print(f"  {loc!r:34} cs_ids={n:6}  qty={qty}")

        print("\n== B. 美仓有库存电池（CS- 前缀, status=1, location LIKE %US%）==")
        q = text("""
            SELECT p.category, COUNT(*) AS n,
                   SUM(p.capacity <> '')      AS has_cap,
                   SUM(p.voltage <> '')       AS has_v,
                   SUM(p.battery_type <> '')  AS has_bt,
                   SUM(p.fit_model <> '')     AS has_fit,
                   SUM(p.part_no <> '')       AS has_pn,
                   SUM(p.dimension <> '')     AS has_dim,
                   SUM(p.net_weight_g > 0)    AS has_wt,
                   SUM(p.wh_value > 0)        AS has_wh
            FROM cs_product p
            WHERE p.cs_id LIKE 'CS-%%' AND p.status = 1
              AND p.cs_id IN (SELECT cs_id FROM cs_inventory
                              WHERE quantity > 0 AND location LIKE '%%US%%')
            GROUP BY p.category ORDER BY n DESC
        """)
        rows = c.execute(q).all()
        skip = {"Mobile, SmartPhone", "Notebook, Laptop", "Camera"}
        tot = sum(r[1] for r in rows)
        skp = sum(r[1] for r in rows if r[0] in skip)
        print(f"  类目数={len(rows)}  美仓记录={tot}  跳过三类={skp}  待分类={tot - skp}")
        for cat, n, cap, v, bt, fit, pn, dim, wt, wh in rows:
            flag = "  [SKIP]" if cat in skip else ""
            print(f"  {cat!r:36} n={n:5} cap={cap:5} volt={v:5} chem={bt:5} "
                  f"fit={fit:5} pno={pn:5} dim={dim:5} wt={wt:5} wh={wh:5}{flag}")

    with shop.connect() as s:
        print("\n== C1. products.product_type 分布（镜像 store=1）==")
        rows = s.execute(text(
            "SELECT product_type, status, COUNT(*) FROM products WHERE store_id=1 "
            "GROUP BY product_type, status ORDER BY COUNT(*) DESC LIMIT 45")).all()
        for pt, st, n in rows:
            print(f"  {pt!r:40} {st:9} {n}")
        n_all, n_pt, n_act = s.execute(text(
            "SELECT COUNT(*), COUNT(DISTINCT product_type), "
            "SUM(status='active') FROM products WHERE store_id=1")).one()
        print(f"  ... 总产品={n_all} active={n_act} product_type 去重={n_pt}")

        print("\n== C2. collections / 关联 / metafields（镜像）==")
        for label, sql in [
            ("collections 总数", "SELECT COUNT(*), COALESCE(SUM(is_smart),0) FROM collections WHERE store_id=1"),
            ("collections 样例", "SELECT title, is_smart, published_at IS NOT NULL FROM collections WHERE store_id=1 ORDER BY id DESC LIMIT 12"),
            ("product_collections", "SELECT COUNT(*) FROM product_collections"),
            ("metafields", "SELECT owner_resource, namespace, `key`, COUNT(*) FROM metafields WHERE store_id=1 GROUP BY owner_resource, namespace, `key` LIMIT 15"),
        ]:
            print(f"  -- {label} --")
            try:
                for r in s.execute(text(sql)).all():
                    print(f"  {tuple(r)}")
            except Exception as ex:  # noqa: BLE001
                print(f"  ERR {ex}")

    print("\nDATA-PROBE-OK")


if __name__ == "__main__":
    sys.exit(main())
