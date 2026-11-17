# -*- coding: utf-8 -*-
"""验证层: B2 遗留draft 的创建时间/线上状态抽查 + C2 逐记录级复核(只读)。"""
import sys
import json
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)
from shopify_admin.services.products.sync_shopify import (  # noqa: E402
    CsShopifySyncService, _is_battery_record,
)
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

with get_cs_engine().connect() as c:
    sold = {r[0]: int(r[1] or 0) for r in c.execute(text("""
        SELECT l.cs_id, SUM(-l.change_qty) FROM cs_inventory_log l
        WHERE l.change_qty < 0 GROUP BY l.cs_id"""))}
    inv = {r[0]: int(r[1] or 0) for r in c.execute(text(
        "SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id"))}

catalog = CsShopifySyncService.load_cs_catalog()

with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid, p.status, p.id,
               DATE(p.created_at)
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
    """)).fetchall()
mirror: dict[str, dict] = {}
for csid, st, pid, cdate in rows:
    d = mirror.setdefault(csid, dict(sts=set(), pids=set(), dates=set()))
    d["sts"].add(st)
    d["pids"].add(pid)
    d["dates"].add(str(cdate))

# ---- B2 创建时间分布 ----
b2 = []
for csid in sold:
    mir = mirror.get(csid)
    if not mir or "active" in mir["sts"]:
        continue
    recs = [r for r in catalog.items() if r[0][0] == csid]
    if any(v["status"] == 1 for _k, v in recs):
        b2.append(csid)
dates = Counter()
for csid in b2:
    for dte in mirror[csid]["dates"]:
        dates[dte] += 1
print(f"B2(遗留draft+CS在售)={len(b2)}  产品创建日期分布:")
for dte, n in dates.most_common(12):
    print(f"  {dte}: {n}")

# ---- C2 逐记录级复核 ----
comp = CsShopifySyncService()._compute(1, "report")
to_create = {t["cs_id"] for t in comp["to_create"]}
c2 = [csid for csid in sold
      if csid not in mirror and csid not in to_create]
detail = Counter()
c2_recs = []
for csid in c2:
    recs = [(k, v) for k, v in catalog.items() if k[0] == csid]
    if not recs:
        detail["cs无记录"] += 1
        continue
    combos = Counter((v["status"] == 1, _is_battery_record(v))
                     for _k, v in recs)
    # 组合解读: (alive,battery)
    if (True, True) in combos:
        detail["??有在售电池记录却在to_create外"] += 1
    elif (True, False) in combos and (False, True) in combos:
        detail["分裂:在售=非电池/电池=停售"] += 1
    elif (True, False) in combos:
        detail["在售但非电池(全记录)"] += 1
    elif (False, True) in combos:
        detail["电池但停售(全记录)"] += 1
    else:
        detail["在售/电池双无"] += 1
    if sold[csid] >= 50 and inv.get(csid, 0) > 0:
        c2_recs.append((sold[csid], csid, inv[csid], dict(combos)))
print(f"\nC2(无镜像且不在to_create)={len(c2)}  记录级组合:")
for k, n in detail.most_common():
    print(f"  {k}: {n}")
print("C2 高销量有库存明细TOP8 (alive,bat组合计数):")
for dec, csid, q, combos in sorted(c2_recs, reverse=True)[:8]:
    print(f"  -{dec:>4} {csid:16} 库存{q:>4} {combos}")

# ---- Shopify 线上状态抽查 3 个 B2 ----
spot = sorted(b2, key=lambda x: -sold[x])[:3]
rest = ShopifyRest(StoreService().get_client(1))
for csid in spot:
    pid = sorted(mirror[csid]["pids"])[-1]
    r = rest._request("GET", f"products/{pid}.json",
                      params={"fields": "id,status,handle,created_at"})
    p = r.get("product", {})
    print(f"抽查 {csid}: pid={pid} 线上status={p.get('status')} "
          f"created={p.get('created_at')} handle={p.get('handle')}")
