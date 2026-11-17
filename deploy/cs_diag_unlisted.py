# -*- coding: utf-8 -*-
"""诊断: 有销量的 CS 产品为何未上架(只读不改)。

口径修正: SKU 第一段 = cs_id(如 CS-PHM507MD), 上轮用 part_no 匹配是错的。
归因分层(按 cs_id):
  A active镜像  B draft镜像  C 无镜像
  无镜像细分: cs_inventory 当前库存>0? cs_product_price 有价?
"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)

# ---- A. 有销量集合(cs_inventory_log 有扣减) ----
with get_cs_engine().connect() as c:
    rows = c.execute(text("""
        SELECT p.cs_id, MAX(p.category) cat, MAX(p.part_no) part,
               SUM(-l.change_qty) dec_t,
               SUM(CASE WHEN l.change_qty>0
                        THEN l.change_qty ELSE 0 END) inc_t
        FROM cs_inventory_log l
        JOIN cs_product p ON p.cs_id = l.cs_id
        WHERE l.change_qty < 0
        GROUP BY p.cs_id
    """)).fetchall()
    sold = {r[0]: {"cat": r[1], "part": r[2], "dec": r[3],
                   "inc": r[4] or 0} for r in rows}
    print(f"有扣减(销量)的 cs_id: {len(sold)}")

    # 当前库存(11-06 快照)
    inv = {}
    for csid, q, n in c.execute(text("""
            SELECT cs_id, SUM(quantity) q, COUNT(*) n
            FROM cs_inventory GROUP BY cs_id""")):
        inv[csid] = (q or 0, n)

    # 价格覆盖
    priced = set()
    for (csid,) in c.execute(text(
            "SELECT DISTINCT cs_id FROM cs_product_price")):
        priced.add(csid)
    print(f"cs_inventory 产品数: {len(inv)} | 有价格: {len(priced)}")

# ---- B. 镜像状态 ----
with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid,
               MAX(p.status),
               COUNT(*) nvar
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
        GROUP BY SUBSTRING_INDEX(pv.sku, '_', 1)
    """)).fetchall()
    mirror = {r[0]: (r[1], r[2]) for r in rows}

# ---- C. 归因 ----
buckets = Counter()
med_missing, active_list, no_mirror_with_stock = [], [], []
for csid, v in sold.items():
    st, nv = mirror.get(csid, (None, 0))
    cur_q, nrow = inv.get(csid, (0, 0))
    has_price = csid in priced
    if st == "active":
        buckets["A active在架"] += 1
        active_list.append((v["dec"], csid, v["cat"], v["part"]))
    elif st is not None:
        buckets[f"B 镜像={st}(下架/草稿)"] += 1
        if cur_q > 0:
            no_mirror_with_stock.append(
                (v["dec"], csid, st, cur_q, v["cat"], v["part"]))
    else:
        key = ("C1 无镜像+有库存" if cur_q > 0
               else "C2 无镜像+零库存")
        if cur_q > 0 and has_price:
            key += "+有价"
        elif cur_q > 0:
            key += "+无价"
        buckets[key] += 1
        if v["cat"] == "Medical":
            med_missing.append((v["dec"], csid, cur_q, has_price,
                                v["part"]))

print("\n=== 归因统计(有销量的产品) ===")
for k, n in buckets.most_common():
    print(f"  {k}: {n}")

print("\n=== C1/C2 医疗明细 TOP12(扣减, cs_id, 当前库存, 有价) ===")
for dec, csid, q, hp, part in sorted(
        med_missing, reverse=True)[:12]:
    print(f"  -{dec:>4} {csid:18} 库存{q:>4} "
          f"{'有价' if hp else '无价'} part={str(part)[:24]}")

print(f"\n=== 下架/草稿且有库存: {len(no_mirror_with_stock)} ===")
for dec, csid, st, q, cat, part in sorted(
        no_mirror_with_stock, reverse=True)[:10]:
    print(f"  -{dec:>4} {csid:18} [{st}] 库存{q:>4} "
          f"{str(cat)[:10]} {str(part)[:20]}")
