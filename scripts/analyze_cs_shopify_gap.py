# -*- coding: utf-8 -*-
"""CS 产品库 ↔ 店铺(Shopify 镜像) 一致性实证分析（只读，不写任何库）。

量化：
1. CS 产品库规模/在售率/零售价覆盖度/数据质量
2. 店铺变体 cs_id 锚定率、SKU 形态（裸 CS-ID vs 带后缀）
3. 三向差异：待发布(CS有店铺无) / 待更新(价格·重量·条码漂移) / 待下架(CS停产店铺在售)
4. 价格漂移分布（防错价护栏阈值实证）
"""
from __future__ import annotations

import re
from collections import Counter
from decimal import Decimal

from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope
from shopify_admin.models.product import Product, ProductVariant

CS_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")

# ---------- 1. CS 产品库画像 ----------
with get_cs_engine().connect() as c:
    rows = c.execute(text(
        "SELECT cs_id, brand, part_no, capacity, voltage, battery_type, net_weight_g, "
        "gross_weight_g, bar_code, suggested_retail_price, status "
        "FROM cs_product"
    )).all()

cs = {r[0].strip(): r for r in rows if r[0]}
on_sale = {k: v for k, v in cs.items() if int(v[10] or 0) == 1}
has_price = {k: v for k, v in on_sale.items() if Decimal(str(v[9] or 0)) > 0}
has_barcode = {k: v for k, v in on_sale.items() if (v[8] or "").strip()}
has_weight = {k: v for k, v in on_sale.items() if int(v[6] or 0) > 0 or int(v[7] or 0) > 0}
print(f"[CS 产品库] 总量={len(cs)} 在售={len(on_sale)} 停产={len(cs) - len(on_sale)}")
print(f"  在售中: 建议零售价>0 = {len(has_price)} ({len(has_price)*100//max(len(on_sale),1)}%)  "
      f"有条码={len(has_barcode)}  有重量={len(has_weight)}")

# ---------- 2. 店铺变体锚定 ----------
with session_scope() as s:
    variants = [
        ((v.sku or "").strip(), v.price, v.grams, (v.barcode or "").strip(),
         v.shopify_variant_id, v.shopify_product_id, v.product_id)
        for v in s.query(ProductVariant).all()
    ]
    prod_status = dict(
        (p.id, p.status) for p in s.query(Product.id, Product.status).all()
    )

anchored: dict[str, list] = {}
no_anchor = []
sku_exact = 0
for sku, price, grams, barcode, vid, spid, pid in variants:
    m = CS_RE.match(sku)
    if not m:
        no_anchor.append(sku)
        continue
    anchored.setdefault(m.group(1), []).append((sku, price, grams, barcode, vid, spid, pid))
    if sku == m.group(1):
        sku_exact += 1

n_var = sum(len(v) for v in anchored.values())
multi = sum(1 for v in anchored.values() if len(v) > 1)
print(f"\n[店铺变体] 总量={len(variants)} 锚定到CS={n_var}({n_var*100//max(len(variants),1)}%) "
      f"无锚点(非CS域)={len(no_anchor)}")
print(f"  唯一cs_id={len(anchored)}  一CS多变体={multi}  SKU=裸CS-ID={sku_exact} 带后缀={n_var - sku_exact}")
if no_anchor[:5]:
    print(f"  无锚点样例: {no_anchor[:5]}")

# ---------- 3. 三向差异 ----------
cs_ids = set(anchored)
to_publish = [k for k in on_sale if k not in cs_ids]
to_archive = [k for k in cs_ids if k in cs and int(cs[k][10] or 0) == 0]
unknown = [k for k in cs_ids if k not in cs]
print(f"\n[三向差异]")
print(f"  待发布(CS在售·店铺无): {len(to_publish)}")
print(f"  待下架(店铺在售·CS停产): {len(to_archive)}")
print(f"  疑似孤儿(店铺有·CS库无): {len(unknown)}  样例: {unknown[:5]}")

# ---------- 4. 字段漂移（价格/重量/条码） ----------
price_drift, price_jump50, weight_drift, barcode_drift, ok = [], [], [], [], 0
samples_p, samples_w = [], []
for csid, vs in anchored.items():
    src = on_sale.get(csid)
    if src is None:
        continue
    retail = Decimal(str(src[9] or 0))
    grams_src = int(src[7] or src[6] or 0)
    bar_src = (src[8] or "").strip()
    for sku, price, grams, barcode, vid, spid, pid in vs:
        if retail > 0 and price is not None:
            d = Decimal(str(price))
            if d != retail:
                price_drift.append((csid, sku, str(d), str(retail)))
                if d > 0 and retail > 0 and abs(float(d) - float(retail)) / float(retail) > 0.5:
                    price_jump50.append((csid, sku, str(d), str(retail)))
            else:
                ok += 1
        if grams_src > 0 and (grams or 0) > 0 and abs(int(grams or 0) - grams_src) > 1:
            weight_drift.append((csid, sku, int(grams or 0), grams_src))
            if len(samples_w) < 5:
                samples_w.append((sku, int(grams or 0), grams_src))
        if bar_src and barcode != bar_src:
            barcode_drift.append((csid, sku, barcode, bar_src))
print(f"\n[字段漂移] (仅统计 CS 在售且源值有效的锚定变体)")
print(f"  价格一致={ok}  漂移={len(price_drift)}  其中>50%跳变={len(price_jump50)}")
for x in price_drift[:5]:
    print(f"    例: {x[1]} 店铺${x[2]} vs CS零售${x[3]}")
for x in price_jump50[:5]:
    print(f"    跳变: {x[1]} 店铺${x[2]} vs CS零售${x[3]}")
print(f"  重量漂移={len(weight_drift)}  例: {samples_w}")
print(f"  条码漂移={len(barcode_drift)}")

# ---------- 5. 店铺侧状态分布 ----------
print(f"\n[店铺产品状态] {Counter(prod_status.values())}")
print("\nANALYSIS DONE")
