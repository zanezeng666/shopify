# -*- coding: utf-8 -*-
"""探针: cs_inventory_log.snapshot_date 时间分布 + 时间列语义(只读)。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import get_cs_engine  # noqa: E402

with get_cs_engine().connect() as c:
    rows = c.execute(text("""
        SELECT DATE_FORMAT(snapshot_date, '%Y-%m') ym,
               COUNT(*) n, COUNT(DISTINCT cs_id) csids,
               SUM(change_qty < 0) negs
        FROM cs_inventory_log
        GROUP BY ym ORDER BY ym DESC LIMIT 15
    """)).fetchall()
    print("snapshot_date 月分布(倒序):")
    for ym, n, csids, negs in rows:
        print(f"  {ym}: 记录{n:>8} csid{csids:>6} 出库记录{negs:>8}")
    r = c.execute(text(
        "SELECT MIN(created_at), MAX(created_at), "
        "MIN(snapshot_date), MAX(snapshot_date) FROM cs_inventory_log"
    )).fetchone()
    print(f"created_at: {r[0]} ~ {r[1]}")
    print(f"snapshot_date: {r[2]} ~ {r[3]}")
    # created_at 维度的近90天出货对照
    sold90c = c.execute(text("""
        SELECT COUNT(DISTINCT cs_id) FROM cs_inventory_log
        WHERE change_qty < 0 AND created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    """)).fetchone()[0]
    allsold = c.execute(text("""
        SELECT COUNT(DISTINCT cs_id) FROM cs_inventory_log WHERE change_qty < 0
    """)).fetchone()[0]
    print(f"created_at口径: 近90天出货 {sold90c} / 全历史 {allsold}")
