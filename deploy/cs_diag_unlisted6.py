# -*- coding: utf-8 -*-
"""取证6: archive_three 断点名单 vs B2 匹配 + 未匹配者的 product_type(只读)。"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)

with get_cs_engine().connect() as c:
    sold = {r[0]: int(r[1] or 0) for r in c.execute(text("""
        SELECT l.cs_id, SUM(-l.change_qty) FROM cs_inventory_log l
        WHERE l.change_qty < 0 GROUP BY l.cs_id"""))}
    st_rows = c.execute(text(
        "SELECT cs_id, status, COUNT(*) FROM cs_product GROUP BY cs_id, status"
    )).fetchall()
cs_stat: dict[str, Counter] = {}
for csid, st, n in st_rows:
    cs_stat.setdefault(csid, Counter())[int(st)] = int(n)

with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid,
               p.status, p.shopify_product_id, p.product_type, p.title
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
    """)).fetchall()
mirror: dict[str, dict] = {}
for csid, st, spid, ptype, title in rows:
    d = mirror.setdefault(csid, dict(sts=set(), spids={}, types=set()))
    d["sts"].add(st)
    d["spids"][int(spid)] = (ptype, title)

def alive(csid):
    return any(k == 1 for k in cs_stat.get(csid, {}))

b2 = [csid for csid in sold
      if mirror.get(csid) and "active" not in mirror[csid]["sts"]
      and alive(csid)]

archived_gids = set()
with open("/tmp/classify_archive_done.txt") as f:
    for line in f:
        line = line.strip()
        if line:
            archived_gids.add(int(line.rsplit("/", 1)[-1]))
print(f"archive_three 断点名单: {len(archived_gids)} 个 gid")

hit, miss = 0, 0
miss_types, miss_list = Counter(), []
for csid in b2:
    spids = mirror[csid]["spids"]
    if any(sp in archived_gids for sp in spids):
        hit += 1
    else:
        miss += 1
        for sp, (ptype, title) in spids.items():
            miss_types[str(ptype)[:30]] += 1
        if sold[csid] >= 30:
            miss_list.append((sold[csid], csid,
                              [str(t)[:26] for t in mirror[csid]["types"]],
                              list(spids.values())[0][0]))
print(f"B2={len(b2)} | archive_three 打的: {hit} | 不是它打的: {miss}")
print("\n未命中者的 product_type 分布:")
for t, n in miss_types.most_common(15):
    print(f"  {t}: {n}")
print("\n未命中且销量>=30 明细TOP12 (csid, CS类目, Shopify product_type):")
for dec, csid, cats, ptype in sorted(miss_list, reverse=True)[:12]:
    print(f"  -{dec:>4} {csid:16} {'/'.join(cats)[:24]:26} {str(ptype)[:30]}")
