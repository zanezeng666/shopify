# -*- coding: utf-8 -*-
"""终局取证: 定价引擎 delist_stopped 误杀验证(只读)。

假设: load_stopped 的 s1=「cs_product 任一记录 status=0 → 整 cs_id 停售」,
      多品牌记录 csid(部分停售部分在售)被误判 → 每日 job_recalc_prices 打成 draft。
验证:
  1) B2(有销量+CS在售+镜像draft) 有多少 csid ∈ load_stopped
  2) 这些 csid 的 cs_product 记录状态分布(混合=误杀铁证)
  3) 线上还在架的产品里, 有多少 csid 明晚还会被误杀(active at risk)
  4) task_result 时间线: recalc_prices 每晚 delist 数
  5) 抽查 B2 产品 Shopify 线上真实 status
"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)
from shopify_admin.services.pricing.service import PricingService  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

with get_cs_engine().connect() as c:
    sold = {r[0]: int(r[1] or 0) for r in c.execute(text("""
        SELECT l.cs_id, SUM(-l.change_qty) FROM cs_inventory_log l
        WHERE l.change_qty < 0 GROUP BY l.cs_id"""))}
    # cs_product 记录级状态: csid -> {status: n_records}
    st_rows = c.execute(text(
        "SELECT cs_id, status, COUNT(*) FROM cs_product GROUP BY cs_id, status"
    )).fetchall()
cs_stat: dict[str, Counter] = {}
for csid, st, n in st_rows:
    cs_stat.setdefault(csid, Counter())[int(st)] = int(n)

def alive(csid):
    return any(k == 1 for k in cs_stat.get(csid, {}))

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

stopped = PricingService().load_stopped()
print(f"load_stopped 停售集={len(stopped)}")

# ---- 1/2. B2 误杀验证 ----
b2 = [csid for csid in sold
      if mirror.get(csid) and "active" not in mirror[csid]["sts"]
      and alive(csid)]
b2_in_stopped = [x for x in b2 if x in stopped]
mixed = [x for x in b2_in_stopped
         if set(cs_stat.get(x, {})) == {0, 1}]
print(f"B2(有销量+CS在售+draft/archived)={len(b2)}")
print(f"  其中 ∈load_stopped: {len(b2_in_stopped)}")
print(f"  其中 cs_product 记录 0/1 混合(部分品牌停售误杀全csid): {len(mixed)}")
top = sorted(mixed, key=lambda x: -sold[x])[:6]
for csid in top:
    print(f"    例证 -{sold[csid]:>4} {csid:16} 记录状态分布={dict(cs_stat[csid])}")

# ---- 3. 线上在架但明晚会被误杀的(active at risk) ----
at_risk, at_risk_sold = [], 0
for csid, d in mirror.items():
    if "active" not in d["sts"]:
        continue
    if csid in stopped and alive(csid):
        at_risk.append(csid)
        at_risk_sold += 1 if csid in sold else 0
print(f"\n线上在架 且 csid∈stopped 且 仍有status=1记录(将持续被误杀): "
      f"{len(at_risk)} csid (其中有销量 {at_risk_sold})")

# ---- 4. task_result 时间线 ----
with get_engine().connect() as m:
    tr = m.execute(text(
        "SELECT task_name, started_at, result FROM task_result "
        "WHERE task_name LIKE '%recalc_prices%' "
        "ORDER BY started_at DESC LIMIT 10")).fetchall()
print("\nrecalc_prices 执行记录(倒序):")
for name, ts, res in tr:
    frag = str(res)
    dl = ""
    if "delist" in frag:
        i = frag.find("delist")
        dl = frag[i:i+40]
    print(f"  {ts} | {dl or frag[:80]}")

# ---- 5. 抽查线上状态 ----
rest = ShopifyRest(StoreService().get_client(1))
spot = sorted(b2_in_stopped, key=lambda x: -sold[x])[:3]
for csid in spot:
    pid = sorted(mirror[csid]["pids"])[-1]
    p = rest.product(int(pid))
    print(f"抽查 {csid}: pid={pid} 线上status={p.get('status')} "
          f"updated_at={p.get('updated_at')}")
