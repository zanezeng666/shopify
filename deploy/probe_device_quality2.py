# -*- coding: utf-8 -*-
"""只读深探 v3：修正 DATE 列比较，补齐覆盖统计。"""
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope


def main() -> None:
    eng = get_cs_engine()
    with eng.connect() as c:
        dev_cs = set(r[0] for r in c.execute(
            text("SELECT DISTINCT cs_id FROM device WHERE cs_id IS NOT NULL")).all())
        prod_cs = set(r[0] for r in c.execute(
            text("SELECT DISTINCT cs_id FROM cs_product WHERE cs_id IS NOT NULL")).all())
        total = c.execute(text("SELECT COUNT(*) FROM device")).scalar()
        for col, is_date in (("release_date", True), ("battery_capacity", False),
                             ("battery_voltage", False), ("c_battery_voltage", False),
                             ("c_battery_capacity", False), ("usage_scene", False)):
            cond = f"{col} IS NOT NULL" if is_date else f"{col} IS NOT NULL AND {col}<>''"
            n = c.execute(text(f"SELECT COUNT(*) FROM device WHERE {cond}")).scalar()
            print(f"填充率 {col}: {n}/{total} ({n*100//total}%)")
        short = c.execute(text(
            "SELECT COUNT(*) FROM device WHERE CHAR_LENGTH(TRIM(device_model))<=2"
        )).scalar()
        print(f"device_model<=2字符: {short} 行")

    print(f"\ndevice.cs_id distinct={len(dev_cs)}")
    print(f"cs_product.cs_id distinct={len(prod_cs)}")
    print(f"device∩cs_product={len(dev_cs & prod_cs)} (占device侧 "
          f"{len(dev_cs & prod_cs)*100//max(len(dev_cs),1)}%)")

    with session_scope() as s:
        rows = s.execute(text(
            "SELECT v.sku FROM product_variants v JOIN products p ON p.id=v.product_id "
            "AND p.store_id=v.store_id WHERE p.store_id=1 AND p.status='active' "
            "AND v.sku LIKE 'CS-%'"
        )).all()
    sku_cs = set(sku.split("_")[0] for (sku,) in rows if len(sku.split("_")) >= 2)
    print(f"镜像active变体 distinct cs_id={len(sku_cs)}")
    print(f"在线∩device={len(sku_cs & dev_cs)} (在线侧覆盖 "
          f"{len(sku_cs & dev_cs)*100//max(len(sku_cs),1)}%)")
    print(f"device 有而店内无（含 draft）={len(dev_cs - sku_cs)}")

    with eng.connect() as c:
        med = c.execute(text(
            "SELECT COUNT(DISTINCT cs_id) FROM device WHERE category LIKE '%Medical%'"
        )).scalar()
        med_models = c.execute(text(
            "SELECT brand, COUNT(DISTINCT device_model) n FROM device "
            "WHERE category LIKE '%Medical%' GROUP BY brand ORDER BY n DESC LIMIT 8"
        )).all()
        print(f"\nMedical 类: distinct cs_id={med} 机型top品牌={[(r[0], r[1]) for r in med_models]}")
        # 反向聚合预览：一个机型平均对应多少 cs_id（SKU 推荐列表规模依据）
        agg = c.execute(text(
            "SELECT AVG(n), MAX(n) FROM (SELECT COUNT(DISTINCT cs_id) n FROM device "
            "WHERE device_model IS NOT NULL AND device_model<>'' "
            "GROUP BY device_model) t"
        )).all()
        print(f"每机型平均适配 cs_id={round(float(agg[0][0]),2)} 最大={agg[0][1]}")


if __name__ == "__main__":
    main()
