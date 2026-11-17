# -*- coding: utf-8 -*-
"""只读深探：cs_new.device 表数据质量画像（为清洗方案与搜索 API 设计提供事实）。"""
import re

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope

CORE_RX = re.compile(r"^(CR|ICR|INR|NCR|UR|LR|LF|IMR|Li[- ]?ion|Li[- ]?po)[- ]?\d{4,5}", re.I)


def main() -> None:
    eng = get_cs_engine()
    with eng.connect() as c:
        cols = [(r[0], r[1]) for r in c.execute(text("SHOW COLUMNS FROM device")).all()]
        print("device 全列:", [f"{n}:{t}" for n, t in cols])

        total = c.execute(text("SELECT COUNT(*) FROM device")).scalar()
        null_model = c.execute(
            text("SELECT COUNT(*) FROM device WHERE device_model IS NULL OR device_model=''")
        ).scalar()
        print(f"\n总行={total}  device_model空={null_model}")

        # 文本列里带"无效/跳过"标记的行分布（找备注列）
        text_cols = [n for n, t in cols if t.lower().startswith(("varchar", "text", "longtext"))]
        for col in text_cols:
            n = c.execute(text(
                f"SELECT COUNT(*) FROM device WHERE {col} LIKE '%无效%' OR {col} LIKE '%跳过%'"
            )).scalar()
            if n:
                print(f"  列 {col} 含无效/跳过标记: {n} 行")

        # brand 质量
        rows = c.execute(text(
            "SELECT brand, COUNT(*) n FROM device WHERE device_model IS NOT NULL "
            "AND device_model<>'' GROUP BY brand ORDER BY n DESC LIMIT 20"
        )).all()
        nb = c.execute(text(
            "SELECT COUNT(DISTINCT brand) FROM device WHERE brand IS NOT NULL AND brand<>''"
        )).scalar()
        nb_null = c.execute(text(
            "SELECT COUNT(*) FROM device WHERE brand IS NULL OR brand=''"
        )).scalar()
        print(f"\nbrand: distinct={nb} 空值行={nb_null}  top20={[(r[0], r[1]) for r in rows]}")

        # device_model 质量：规范化后 distinct、疑似电芯型号
        agg = c.execute(text(
            "SELECT UPPER(TRIM(REPLACE(device_model,'  ',' '))) m, COUNT(*) n "
            "FROM device WHERE device_model IS NOT NULL AND device_model<>'' "
            "GROUP BY m ORDER BY n DESC LIMIT 15"
        )).all()
        dm = c.execute(text(
            "SELECT COUNT(DISTINCT UPPER(TRIM(device_model))) FROM device "
            "WHERE device_model IS NOT NULL AND device_model<>''"
        )).scalar()
        print(f"\ndevice_model: 规范化distinct={dm}")
        print("  top15:", [(r[0], r[1]) for r in agg])

        # 疑似电芯型号（脏数据主力）
        all_models = c.execute(text(
            "SELECT DISTINCT device_model FROM device WHERE device_model IS NOT NULL AND device_model<>''"
        )).all()
        core_like = [m[0] for m in all_models if CORE_RX.match(m[0].strip())]
        print(f"  疑似电芯型号 distinct={len(core_like)} 样本={core_like[:8]}")

        # cs_id 在 cs_product 的覆盖率 + category 分布
        cat = c.execute(text(
            "SELECT category, COUNT(*) n FROM device GROUP BY category ORDER BY n DESC LIMIT 12"
        )).all()
        print("\ncategory top12:", [(r[0], r[1]) for r in cat])
        cov = c.execute(text(
            "SELECT COUNT(DISTINCT d.cs_id) FROM device d "
            "JOIN cs_product p ON p.cs_id=d.cs_id"
        )).scalar()
        dcov = c.execute(text("SELECT COUNT(DISTINCT cs_id) FROM device")).scalar()
        print(f"cs_id: device侧distinct={dcov}  在cs_product命中={cov}")

        # release_date / battery 字段填充率（判断可用列）
        for col in ("release_date", "battery_capacity", "c_battery_voltage", "battery_type"):
            n = c.execute(text(
                f"SELECT COUNT(*) FROM device WHERE {col} IS NOT NULL AND {col}<>''"
            )).scalar()
            print(f"  填充率 {col}: {n}/{total} ({n*100//total}%)")

    # 跨库：device cs_id 与镜像在线变体的覆盖（拉集合到 python 算，避开跨库 JOIN collation 坑）
    with get_cs_engine().connect() as c:
        cs_all = set(r[0] for r in c.execute(text(
            "SELECT DISTINCT cs_id FROM device WHERE cs_id IS NOT NULL"
        )).all())
    with session_scope() as s:
        # 镜像在线口径：sku 前缀 CS- 的变体（status 用收缩后本地 active 近似，另报全量）
        rows = s.execute(text(
            "SELECT v.sku FROM product_variants v JOIN products p ON p.id=v.product_id "
            "AND p.store_id=v.store_id WHERE p.store_id=1 AND p.status='active' AND v.sku LIKE 'CS-%'"
        )).all()
    sku_csids = set()
    for (sku,) in rows:
        parts = sku.split("_")
        if len(parts) >= 2:
            sku_csids.add(parts[0])  # CS-XXXX
    inter_online = cs_all & sku_csids
    print(f"\n镜像active变体CS口径: distinct cs_id={len(sku_csids)}  device表覆盖={len(inter_online)} "
          f"({len(inter_online)*100//max(len(sku_csids),1)}%)")


if __name__ == "__main__":
    main()
