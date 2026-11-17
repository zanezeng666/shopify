# -*- coding: utf-8 -*-
"""v8：collation 修复（Python 侧交集）+ 停售明细 + 逐 cs_id 最新快照覆盖。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    print("== 停售：cs_product.status=0 明细 ==")
    rows = c.execute(text(
        "SELECT DISTINCT cs_id FROM cs_new.cs_product WHERE status=0")).all()
    stopped1 = {r[0] for r in rows}
    print("   cs_id 数:", len(stopped1), sorted(stopped1)[:12])

    print("\n== record 最新一条为 Stop/Delete 的 cs_id ==")
    rows = c.execute(text(
        "SELECT r.cs_id FROM cs_new.cs_product_record r "
        "JOIN (SELECT cs_id, MAX(id) mid FROM cs_new.cs_product_record "
        "      GROUP BY cs_id) t ON t.mid=r.id "
        "WHERE r.status IN ('Stop Production','Delete','Stop Limit In Stock')")).all()
    stopped2 = {r[0] for r in rows}
    print("   数:", len(stopped2), sorted(stopped2)[:12])

    print("\n== 停售并集 vs Shopify 在售（shopify_new 有哪些表先看一眼） ==")
    tabs = c.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='shopify_new' ORDER BY table_name")).all()
    print("   shopify_new 表:", [t[0] for t in tabs])

    print("\n== 逐 cs_id 自身最新快照：amazon 价覆盖（Python 交集） ==")
    # 拉所有 amazon_inventory 的 (cs_id, add_date) 去掉空 cs_id
    rows = c.execute(text(
        "SELECT cs_id, add_date, price, store_name FROM amazon.amazon_inventory "
        "WHERE cs_id IS NOT NULL AND cs_id<>'' "
        "AND price IS NOT NULL AND CAST(price AS DECIMAL(10,2))>0")).all()
    print("   amazon_inventory 有效行:", len(rows))
    cs_ids = c.execute(text(
        "SELECT DISTINCT cs_id FROM cs_new.cs_product")).all()
    csset = {r[0] for r in rows and ()} if False else {r[0] for r in c.execute(text(
        "SELECT DISTINCT cs_id FROM cs_new.cs_product")).all()}
    print("   cs_product distinct cs_id:", len(csset))

    by_cs = {}
    for cs_id, d, p, s in rows:
        by_cs.setdefault(cs_id, []).append((d, float(p), s))
    latest = {}
    for k, lst in by_cs.items():
        m = max(x[0] for x in lst)
        prices = sorted(x[1] for x in lst if x[0] == m)
        latest[k] = (m, prices)
    cov = set(latest) & csset
    print("   有 amazon 价的 cs_product 产品:", len(cov),
          f"({len(cov)*100//len(csset)}%)")
    noamz = csset - set(latest)
    print("   无 amazon 价（走 P20 公式）:", len(noamz))

    print("\n== 离群剔除效果抽样（v1<v2*0.6 的案例数） ==")
    n_outlier = 0
    samples = []
    for k, (d, ps) in latest.items():
        if len(ps) >= 2 and ps[0] < ps[1] * 0.6:
            n_outlier += 1
            if len(samples) < 5:
                samples.append((k, ps[:4]))
    print("   触发离群剔除的 cs_id 数:", n_outlier)
    for s in samples:
        print("     ", s[0], s[1])

    print("\n== 停售产品中有多少在 amazon_inventory（应下架清单规模） ==")
    print("   status=0:", len(stopped1),
          "record-stop:", len(stopped2),
          "并集:", len(stopped1 | stopped2))
