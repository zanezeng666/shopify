# -*- coding: utf-8 -*-
"""取证5: B2 draft 的线上状态/翻转时间 + launch名单比对 + sync_products 任务史(只读)。"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

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
               p.status, p.shopify_product_id
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
    """)).fetchall()
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

# ---- launch 名单比对 ----
try:
    done = {x.strip() for x in
            open("/tmp/launch_done.txt").read().split() if x.strip()}
except Exception:
    done = set()
inlaunch = [x for x in b2 if x in done]
print(f"B2={len(b2)} | 其中在 /tmp/launch_done.txt={len(inlaunch)} "
      f"| 不在={len(b2) - len(inlaunch)}")

# ---- task_result: sync_products 历史 ----
with get_engine().connect() as m:
    tr = m.execute(text(
        "SELECT started_at, result FROM task_result "
        "WHERE task_name LIKE '%sync_products%' "
        "ORDER BY started_at DESC LIMIT 8")).fetchall()
print("\nsync_products 执行记录(倒序):")
for ts, res in tr:
    print(f"  {ts} | {str(res)[:110]}")

# ---- 线上抽查 TOP5 (正确的 shopify_product_id) ----
rest = ShopifyRest(StoreService().get_client(1))
spot = sorted(b2, key=lambda x: -sold[x])[:5]
for csid in spot:
    spid = sorted(mirror[csid]["spids"])[-1]
    p = rest.product(spid)
    print(f"{csid}: spid={spid} 线上status={p.get('status')} "
          f"created={str(p.get('created_at'))[:19]} "
          f"updated={str(p.get('updated_at'))[:19]} "
          f"pub={str(p.get('published_at'))[:19]}")

# ---- 全量: 用 GraphQL 批量拿 B2 线上 status/updated 日期分布 ----
cl = rest.client
upd_days, st_online = Counter(), Counter()
spids = sorted({sorted(mirror[x]["spids"])[-1] for x in b2})
for i in range(0, len(spids), 50):
    chunk = spids[i:i + 50]
    ids = " ".join(f'p{j}: product(id: "gid://shopify/Product/{s}") '
                   f'{{ status updatedAt }}' for j, s in enumerate(chunk))
    r = cl.graphql("{" + ids + "}")
    data = r.get("data") or r
    for j, s in enumerate(chunk):
        node = (data.get(f"p{j}") or {}) if isinstance(data, dict) else {}
        if not node:
            st_online["查询失败"] += 1
            continue
        st_online[node.get("status")] += 1
        upd_days[str(node.get("updatedAt", ""))[:10]] += 1
print(f"\nB2 线上状态分布: {dict(st_online)}")
print("线上 updatedAt 日期分布 TOP10:")
for d, n in upd_days.most_common(10):
    print(f"  {d}: {n}")
