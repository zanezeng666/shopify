# -*- coding: utf-8 -*-
"""深度归因: 有销量未上架产品逐个定责(只读)。

上一轮(cs_diag_unlisted.py)粗分 A/B/C, 本轮拆根因:
  B(draft/archived) -> B1 被 delist_missing 下架(product num 在 /tmp/delist_done.txt)
                        B2 未被下架=历史遗留 draft 从未被激活
  C(无镜像)        -> C1 当前仍在 to_create(重跑 launch_new 即可补建, 11-06 库存快照后有货)
                        C2 不在 to_create: cs 无记录 / status!=1 停售 / 非电池记录
"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)
from shopify_admin.services.products.sync_shopify import (  # noqa: E402
    CsShopifySyncService, _is_battery_record,
)

# ---- 有销量集合 ----
with get_cs_engine().connect() as c:
    sold = {r[0]: int(r[1] or 0) for r in c.execute(text("""
        SELECT l.cs_id, SUM(-l.change_qty) FROM cs_inventory_log l
        WHERE l.change_qty < 0 GROUP BY l.cs_id"""))}
    inv = {r[0]: (int(r[1] or 0)) for r in c.execute(text(
        "SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id"))}

# ---- CS 目录逐 csid 汇总 ----
catalog = CsShopifySyncService.load_cs_catalog()
by_csid: dict[str, dict] = {}
for (csid, _bl), row in catalog.items():
    d = by_csid.setdefault(csid, dict(exists=1, alive=0, battery=0, cats=set()))
    if row["status"] == 1:
        d["alive"] = 1
    if _is_battery_record(row):
        d["battery"] = 1
    d["cats"].add(row["category"])

# ---- 镜像: csid -> {statuses, product_ids} ----
with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid, p.status, p.id
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
    """)).fetchall()
mirror: dict[str, dict] = {}
for csid, st, pid in rows:
    d = mirror.setdefault(csid, dict(sts=set(), pids=set()))
    d["sts"].add(st)
    d["pids"].add(pid)

# ---- 11-04 下架名单 ----
try:
    delisted_pids = {int(x) for x in
                     open("/tmp/delist_done.txt").read().split() if x.strip()}
except Exception:
    delisted_pids = set()
print(f"有销量 cs_id={len(sold)} | delist_done 名单={len(delisted_pids)}")

# ---- 当前 to_create(重跑 launch_new 会建哪些) ----
comp = CsShopifySyncService()._compute(1, "report")
to_create = {t["cs_id"] for t in comp["to_create"]}
print(f"当前 to_create={len(to_create)}")

# ---- 归因 ----
buckets = Counter()
samples: dict[str, list] = {}
for csid, dec in sold.items():
    mir = mirror.get(csid)
    cs = by_csid.get(csid, dict(exists=0, alive=0, battery=0, cats={"?"}))
    q = inv.get(csid, 0)
    if mir and "active" in mir["sts"]:
        k = "A active在架"
    elif mir:
        hit_delist = bool(mir["pids"] & delisted_pids)
        if hit_delist:
            k = "B1 被下架规则打到(delist_missing)"
        elif not cs["alive"]:
            k = "B2 遗留draft+CS已停售(下次delist也会打)"
        else:
            k = "B2 遗留draft+CS在售(从未被激活,可救)"
        tag = k
    else:
        if csid in to_create:
            k = tag = "C1 在to_create(重跑launch_new即建)"
        elif not cs["exists"]:
            k = tag = "C2 cs目录无记录"
        elif not cs["alive"]:
            k = tag = "C2 CS停售(status!=1)"
        elif not cs["battery"]:
            k = tag = "C2 非电池记录(配件过滤)"
        else:
            k = tag = "C2 其他(在售电池但不在to_create)"
    buckets[k] += 1
    samples.setdefault(tag, []).append((dec, csid, q, cs["alive"], cs["battery"],
                                       "/".join(sorted(cs["cats"]))[:14]))

print("\n=== 深度归因 ===")
for k, n in buckets.most_common():
    print(f"  {k}: {n}")

for key in ("B2 遗留draft+CS在售(从未被激活,可救)",
            "B1 被下架规则打到(delist_missing)",
            "C1 在to_create(重跑launch_new即建)",
            "C2 非电池记录(配件过滤)", "C2 其他(在售电池但不在to_create)"):
    lst = sorted(samples.get(key, []), reverse=True)[:10]
    if lst:
        print(f"\n--- {key} TOP10 (扣减, cs_id, 现库存, cs在售, 电池, 类目) ---")
        for dec, csid, q, al, bt, cat in lst:
            print(f"  -{dec:>5} {csid:16} 库存{q:>4} "
                  f"alive={al} bat={bt} {cat}")
