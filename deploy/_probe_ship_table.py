# -*- coding: utf-8 -*-
"""只读探查: USPS 费率表粒度 + 定价决策的 F 分布 -> 量化'粗'在哪.
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python _probe_ship_table.py
"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing.service import PricingService, PricingConfig  # noqa: E402

svc = PricingService()
cfg = PricingConfig.from_settings()
print(f"cfg: shipping_zone={cfg.shipping_zone} default_weight_g={cfg.default_weight_g}")

# ---- 1. 表里有哪些 zone / carrier ----
from shopify_admin.core.database import get_cs_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402

with get_cs_engine().connect() as c:
    rows = c.execute(text(
        "SELECT carrier_code, zone, COUNT(*) n, MIN(weight_g), MAX(weight_g), "
        "MIN(price), MAX(price) FROM cs_shipping_rate "
        "WHERE carrier_code IN ('usps','cs_usps') GROUP BY carrier_code, zone "
        "ORDER BY carrier_code, zone")).all()
print("\n[1] 费率表概览 (carrier, zone, 档数, 重量范围g, 价格范围):")
for r in rows:
    print(f"  {r[0]} zone{r[1]}: {r[2]} 档, {r[3]}~{r[4]}g, ${r[5]:.2f}~${r[6]:.2f}")

# ---- 2. usps zone9 完整档位 + 与其它 zone 对比 ----
with get_cs_engine().connect() as c:
    z9 = c.execute(text(
        "SELECT weight_g, price FROM cs_shipping_rate "
        "WHERE carrier_code='usps' AND zone=9 ORDER BY weight_g")).all()
print(f"\n[2] usps zone9 完整档位 ({len(z9)} 档):")
for w, p in z9:
    print(f"  <= {w}g: ${p:.2f}")
zones = sorted({r[1] for r in rows if r[0] == "usps"})
if len(zones) > 1:
    print(f"  同重量档跨 zone 价差示例 (zones={zones}):")
    with get_cs_engine().connect() as c:
        for w, _ in z9[:6] + z9[-2:]:
            ps = c.execute(text(
                "SELECT zone, price FROM cs_shipping_rate "
                "WHERE carrier_code='usps' AND weight_g=:w ORDER BY zone"),
                {"w": w}).all()
            line = " ".join(f"z{z}=${p:.2f}" for z, p in ps)
            print(f"    {w}g: {line}")

# ---- 3. 决策 F 分布 + 重量来源 ----
dec = svc.build_decisions()
valid = [d for d in dec.values() if d.ship_cost]
fc = Counter(round(d.ship_cost, 2) for d in valid)
print(f"\n[3] 决策 F 分布 (有效 {len(valid)}):")
for fee, n in fc.most_common(10):
    print(f"  F=${fee:.2f}: {n} SKU ({n / len(valid) * 100:.1f}%)")
no_w = sum(1 for d in valid if d.weight_g == 0)
print(f"  无重量(用默认{cfg.default_weight_g}g 首档计价): {no_w}")
wt = sorted(d.weight_g for d in valid if d.weight_g > 0)
if wt:
    print(f"  重量分布: P25={wt[len(wt)//4]}g 中位={wt[len(wt)//2]}g P75={wt[len(wt)*3//4]}g 最大={wt[-1]}g")
