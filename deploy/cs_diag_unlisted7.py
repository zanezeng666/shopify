# -*- coding: utf-8 -*-
"""终局定量: shrink A档名单 ∩ B2(有销量被下架) 的判据复盘(只读)。"""
import json
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)

with open("/home/jason/shopify-admin/deploy/shrink_draft_ids.json") as f:
    draft_a = set(json.load(f)["draftA"])

with get_cs_engine().connect() as c:
    sold = {r[0]: int(r[1] or 0) for r in c.execute(text("""
        SELECT l.cs_id, SUM(-l.change_qty) FROM cs_inventory_log l
        WHERE l.change_qty < 0 GROUP BY l.cs_id"""))}
    st_rows = c.execute(text(
        "SELECT cs_id, status, COUNT(*) FROM cs_product GROUP BY cs_id, status"
    )).fetchall()
    # 三仓(SZ/HK/US)库存 vs 全仓库存
    inv3 = {r[0] for r in c.execute(text(
        "SELECT DISTINCT cs_id FROM cs_inventory "
        "WHERE location IN ('US','SZ','HK') AND quantity > 0"))}
    invall = {r[0]: int(r[1] or 0) for r in c.execute(text(
        "SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id"))}
    amz = {r[0] for r in c.execute(text(
        "SELECT DISTINCT cs_id FROM amazon.amazon_inventory "
        "WHERE cs_id IS NOT NULL AND cs_id <> '' AND market_id='ATVPDKIKX0DER' "
        "AND price IS NOT NULL AND price <> ''"))}
cs_stat: dict[str, Counter] = {}
for csid, st, n in st_rows:
    cs_stat.setdefault(csid, Counter())[int(st)] = int(n)

with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid,
               p.status, p.shopify_product_id
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
    """)).fetchall()
    # Shopify 店内订单卖过的 cs_id(shrink 当时的"历史销量"口径)
    shop_sold = {r[0] for r in m.execute(text(
        "SELECT DISTINCT cs_id FROM order_items "
        "WHERE cs_id IS NOT NULL AND cs_id <> ''"))}
mirror: dict[str, dict] = {}
for csid, st, spid in rows:
    d = mirror.setdefault(csid, dict(sts=set(), spids=set()))
    d["sts"].add(st)
    d["spids"].add(int(spid))

def alive(csid):
    return any(k == 1 for k in cs_stat.get(csid, {}))

b2 = [csid for csid in sold
      if mirror.get(csid) and "active" not in mirror[csid]["sts"]
      and alive(csid)]

hit = [x for x in b2 if mirror[x]["spids"] & draft_a]
print(f"B2={len(b2)} | ∈shrink A档名单: {len(hit)} | 不在: {len(b2)-len(hit)}")

c1, c2, c3 = Counter(), Counter(), Counter()
tot_dec_shrink = 0
for csid in hit:
    s3 = csid in inv3                     # 当时三仓有货
    sa = csid in amz                      # 有亚马逊参考价
    ss = csid in shop_sold                # 店内有单(shrink口径)
    c1["三仓有货却被下架(因无亚马逊价)" if s3 else "当时三仓无货"] += 1
    if not s3:
        c2["全仓也无货" if invall.get(csid, 0) <= 0 else "货在其他仓"] += 1
    c3["店内有单(不该被打)" if ss else "店内无单(口径漏检)"] += 1
    tot_dec_shrink += sold[csid]
print("判据复盘(对这批有销量的):")
for k, v in c1.most_common():
    print(f"  {k}: {v}")
for k, v in c2.most_common():
    print(f"  {k}: {v}")
for k, v in c3.most_common():
    print(f"  {k}: {v}")
print(f"合计 CS 历史出库量: {tot_dec_shrink} 件")
