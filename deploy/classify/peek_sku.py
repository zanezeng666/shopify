# -*- coding: utf-8 -*-
"""查镜像 SKU 真实形态。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")


def main() -> None:
    from sqlalchemy import text
    from shopify_admin.core.database import get_engine
    e = get_engine()
    with e.connect() as c:
        rows = c.execute(text(
            "SELECT product_id, sku FROM product_variants "
            "WHERE sku LIKE :p1 LIMIT 8"), {"p1": "CS-ACX%"}).fetchall()
        print("-- sku LIKE 'CS-ACX%' --")
        for r in rows:
            print(f"  pid={r[0]} sku={r[1]}")
        rows2 = c.execute(text(
            "SELECT product_id, sku FROM product_variants "
            "WHERE sku LIKE :p2 LIMIT 5"), {"p2": "CS-CS-%"}).fetchall()
        print(f"-- sku LIKE 'CS-CS-%': {len(rows2)} 条 --")
        rows3 = c.execute(text(
            "SELECT COUNT(*) FROM product_variants WHERE sku LIKE :p3"),
            {"p3": "CS-%"}).scalar()
        print(f"-- sku LIKE 'CS-%' 总数: {rows3}")


if __name__ == "__main__":
    main()
