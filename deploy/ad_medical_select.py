# -*- coding: utf-8 -*-
"""医疗电池广告选品闸门。
筛选: product_type='Medical Battery' × PricingService决策(margin>=30%且有亚马逊参考价)
      × cs_inventory有库存(US仓优先)。
输出: deploy/ad_medical_selected.json (打tag/collection/PMax listing group 的输入)
"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from sqlalchemy import text

from shopify_admin.core.database import session_scope, get_cs_engine
from shopify_admin.models.product import Product, ProductVariant
from shopify_admin.services.pricing import PricingService

OUT = "/home/jason/shopify-admin/deploy/ad_medical_selected.json"

# ---- 1) 镜像库: 医疗类目 active 产品 + 变体 ----
prods = {}   # shopify_product_id -> row
with session_scope() as s:
    rows = s.execute(
        text(
            "SELECT p.shopify_product_id, p.handle, p.title, p.product_type, "
            "p.tags, v.sku, v.price, v.shopify_variant_id "
            "FROM products p JOIN product_variants v "
            "ON v.product_id = p.id AND v.store_id = p.store_id "
            "WHERE p.store_id = 1 AND p.status = 'active' "
            "AND p.product_type = 'Medical Battery'"
        )
    ).all()
for r in rows:
    pid, handle, title, ptype, tags, sku, price, vid = r
    d = prods.setdefault(pid, {
        "product_id": pid, "handle": handle, "title": title,
        "tags": tags, "skus": [], "variant_ids": [], "price": None,
    })
    if sku:
        d["skus"].append(sku)
        d["variant_ids"].append(vid)
    if price is not None:
        d["price"] = float(price)
print(f"医疗类目 active 产品: {len(prods)}")

# ---- 2) 定价决策 (cs_id 粒度) ----
svc = PricingService()
decisions = svc.build_decisions()
print(f"定价决策: {len(decisions)}")

# ---- 3) cs_inventory 库存 ----
with get_cs_engine().connect() as conn:
    locs = [r[0] for r in conn.execute(
        text("SELECT DISTINCT location FROM cs_inventory")).all()]
    print("仓库 location 取值:", locs)
    inv_all = {r[0]: int(r[1] or 0) for r in conn.execute(
        text("SELECT cs_id, SUM(quantity) FROM cs_inventory "
             "GROUP BY cs_id")).all()}
    us_loc = next((l for l in locs if str(l).upper().strip() in
                   ("US", "美国仓", "US-W")), None)
    inv_us = {}
    if us_loc is not None:
        inv_us = {r[0]: int(r[1] or 0) for r in conn.execute(
            text("SELECT cs_id, SUM(quantity) FROM cs_inventory "
                 "WHERE location = :l GROUP BY cs_id"),
            {"l": us_loc}).all()}
print(f"库存总口径 cs_id 数: {len(inv_all)}, US仓: {len(inv_us)} "
      f"(us_loc={us_loc})")

# ---- 4) 分布透视 (定门槛用) ----
from collections import Counter

buckets = Counter()
cross = Counter()
for pid, d in prods.items():
    if not d["skus"]:
        continue
    cs_id = d["skus"][0].split("_")[0]
    dec = decisions.get(cs_id)
    if dec is None or dec.stopped or dec.margin is None:
        continue
    m = dec.margin
    b = ("<15%" if m < 0.15 else "15-20%" if m < 0.20 else
         "20-25%" if m < 0.25 else "25-30%" if m < 0.30 else
         "30-40%" if m < 0.40 else ">=40%")
    a = "有A" if dec.amzn_ref else "无A"
    buckets[b] += 1
    cross[(a, b)] += 1
print("\n毛利分布:", dict(buckets))
print("交叉分布:")
for a in ("有A", "无A"):
    print(f"  {a}: " + " ".join(
        f"{b}={cross[(a, b)]}" for b in
        ("<15%", "15-20%", "20-25%", "25-30%", "30-40%", ">=40%")))

# ---- 5) 以量为主选品: 有亚马逊参考价(市场验证) + 有库存, 不卡价格/毛利 ----
sel, rej = [], {"no_sku": 0, "no_decision": 0, "no_stock": 0,
                "no_amzn": 0}
for pid, d in prods.items():
    if not d["skus"]:
        rej["no_sku"] += 1
        continue
    cs_id = d["skus"][0].split("_")[0]     # CS-XXXXX
    dec = decisions.get(cs_id)
    if dec is None or dec.stopped:
        rej["no_decision"] += 1
        continue
    if inv_all.get(cs_id, 0) <= 0:
        rej["no_stock"] += 1
        continue
    if not dec.amzn_ref:
        rej["no_amzn"] += 1
        continue
    ratio = (dec.amzn_ref / dec.price) if dec.price else None
    d.update({
        "cs_id": cs_id, "margin": round(dec.margin or 0, 3),
        "amzn_ref": dec.amzn_ref, "cost": dec.cost,
        "ship_cost": dec.ship_cost, "stock_total": inv_all.get(cs_id, 0),
        "stock_us": inv_us.get(cs_id, 0),
        "ratio": round(ratio, 2) if ratio else None,
    })
    sel.append(d)

sel.sort(key=lambda x: (-(x["ratio"] or 0), -x["stock_us"]))
print(f"\n入选(有A市场验证+有库存, 不卡价格): {len(sel)}")
print("淘汰:", {k: v for k, v in rej.items() if v})
with open(OUT, "w", encoding="utf-8") as f:
    json.dump({"selected": sel, "rejected": rej,
               "total_medical": len(prods)}, f, ensure_ascii=False, indent=1)
print("->", OUT)
r_n = [x for x in sel if (x["ratio"] or 0) >= 1.25]
print(f"其中价格强优势(比值>=1.25): {len(r_n)}")
print("\nTop10 (价格优势↓):")
for x in sel[:10]:
    print(f"  ${x['price']:>6.2f} 毛{x['margin']*100:>3.0f}% "
          f"A=${x['amzn_ref']:>6.2f} 比{x['ratio'] or 0:.2f} "
          f"库存{x['stock_total']:>4} {x['title'][:42]}")
