# -*- coding: utf-8 -*-
"""真库冒烟：build_decisions 全量 + recalc/delist dry-run + 决策分布。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService

svc = PricingService()
decisions = svc.build_decisions()
ds = list(decisions.values())

n = len(ds)
stopped = sum(1 for d in ds if d.stopped)
no_cost = sum(1 for d in ds if d.flag == "no_cost")
priced = [d for d in ds if d.price is not None]
risk = [d for d in priced if d.flag == "margin_risk"]
by_basis = {}
for d in priced:
    by_basis[d.basis] = by_basis.get(d.basis, 0) + 1

print(f"total={n} stopped={stopped} no_cost={no_cost} priced={len(priced)}")
print(f"basis={by_basis} margin_risk={len(risk)}")
margins = sorted(d.margin for d in priced)
if margins:
    import statistics
    print(f"margin: min={margins[0]:.4f} p5={margins[len(margins)//20]:.4f} "
          f"med={statistics.median(margins):.4f} max={margins[-1]:.4f}")
    below15 = [d for d in priced if d.margin < 0.15 - 1e-6]
    print(f"margin<15%的产品数: {len(below15)}")
    for d in below15[:5]:
        print("   !!", d.cs_id, f"cost={d.cost} ship={d.ship_cost} A={d.amzn_ref} "
              f"p15={d.p15:.2f} price={d.price} margin={d.margin:.4f} basis={d.basis}")

prices = sorted(d.price for d in priced)
print(f"price: min={prices[0]} med={prices[len(prices)//2]} max={prices[-1]}")

print("\n== 样本（每种 basis 3 个） ==")
for basis in ("formula20", "amazon_cap", "floor15"):
    sample = [d for d in priced if d.basis == basis][:3]
    for d in sample:
        print(f"   [{basis}] {d.cs_id} cost={d.cost} ship={d.ship_cost} w={d.weight_g}g "
              f"A={d.amzn_ref} p20={d.p20:.2f} p15={d.p15:.2f} → {d.price} "
              f"(margin={d.margin:.1%})")

print("\n== margin_risk 样本（前5） ==")
for d in risk[:5]:
    print(f"   {d.cs_id} cost={d.cost} ship={d.ship_cost} A={d.amzn_ref} "
          f"→ price={d.price} (A×0.97={d.amzn_ref*0.97:.2f})")

# 店铺 dry-run
print("\n== 店铺对账 dry-run ==")
from shopify_admin.services.stores.service import StoreService
for st in StoreService().list_stores(available_only=True):
    r = svc.recalc_store(st["id"], decisions, dry_run=True)
    dl = svc.delist_stopped(st["id"], decisions, dry_run=True)
    print(f"   store{st['id']} {st.get('name','')}: "
          f"vars={r['variants']} to_update={r['to_update']} unchanged={r['unchanged']} "
          f"no_dec={r['no_decision']} stopped_vars={r['stopped_variants']} | "
          f"delist={dl['to_delist']}")

# 决策快照落盘（供部署后核对）
out = {k: d.as_dict() for k, d in decisions.items()}
with open("/tmp/pricing_decisions.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)
print("\nsaved /tmp/pricing_decisions.json")
