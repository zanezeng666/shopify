# -*- coding: utf-8 -*-
"""取证：店铺既有 CS 产品组织模式（多品牌=几产品？）+ 老格式 + to_create 多品牌候选。只读。"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import select

from shopify_admin.core.database import session_scope
from shopify_admin.models.product import Product, ProductVariant
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

# 1) 店铺镜像：按 cs_id 前缀聚合
with session_scope() as s:
    rows = s.execute(
        select(ProductVariant.sku, ProductVariant.shopify_product_id, ProductVariant.price,
               Product.title, Product.handle, Product.vendor, Product.raw)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(ProductVariant.store_id == 1)
    ).all()
print(f"total anchored-ish variants rows: {len(rows)}")

groups: dict[str, dict] = defaultdict(lambda: {"prods": set(), "brands": set(), "skus": [], "meta": {}})
for sku, spid, price, title, handle, vendor, raw in rows:
    m = re.match(r"^(CS-[A-Za-z0-9]+)", sku or "")
    if not m:
        continue
    g = groups[m.group(1)]
    g["prods"].add(spid)
    parts = sku.split("_")
    if len(parts) >= 2:
        g["brands"].add(parts[1])
    g["skus"].append((sku, spid, str(price), title, handle, vendor, raw))
    g["meta"][spid] = (title, handle, vendor)

multi_prod = {k: v for k, v in groups.items() if len(v["prods"]) > 1}
multi_brand_1p = {k: v for k, v in groups.items() if len(v["brands"]) > 1 and len(v["prods"]) == 1}
print(f"cs_id groups: {len(groups)}, multi-PRODUCT groups: {len(multi_prod)}, multi-brand-in-ONE-product: {len(multi_brand_1p)}")
print("multi-product examples:", list(multi_prod)[:5])
print("multi-brand-one-product examples:", list(multi_brand_1p)[:5])

# 2) 取一个多品牌样本完整展示（优先 multi_brand_1p，其次 multi_prod）
sample_key = next(iter(multi_brand_1p), None) or next(iter(multi_prod), None)
if sample_key:
    g = groups[sample_key]
    print(f"\n########## 样本 cs_id={sample_key} ##########")
    print("skus:", [x[0] for x in g["skus"]])
    for spid, (title, handle, vendor) in list(g["meta"].items())[:2]:
        one = next(x for x in g["skus"] if x[1] == spid)
        raw = one[6] or {}
        print(f"\n--- product {spid}: title={title!r} handle={handle!r} vendor={vendor!r}")
        body = (raw.get("body_html") or "")[:900]
        print("body_html[:900]:", body)
        print("tags:", raw.get("tags"), "| options:", raw.get("options"), "| product_type:", raw.get("product_type"))
        print("variants:", [{k: v.get(k) for k in ("sku", "title", "option1", "price", "barcode", "grams")} for v in (raw.get("variants") or [])][:6])

# 3) 单品牌常规样本（同上取一个单产品单品牌 CS 老产品做基准）
plain = [k for k, v in groups.items() if len(v["prods"]) == 1 and len(v["brands"]) <= 1 and v["skus"]]
if plain:
    g = groups[plain[0]]
    one = g["skus"][0]
    raw = one[6] or {}
    print(f"\n########## 基准单品牌老产品 cs_id={plain[0]} product={one[1]} ##########")
    print("title:", one[3], "| handle:", one[4], "| vendor:", one[5])
    print("body_html[:900]:", (raw.get("body_html") or "")[:900])
    print("tags:", raw.get("tags"), "| options:", raw.get("options"), "| product_type:", raw.get("product_type"))
    print("variants:", [{k: v.get(k) for k in ("sku", "title", "option1", "price", "barcode", "grams")} for v in (raw.get("variants") or [])][:6])

# 4) to_create 里找多品牌候选（fit_model 含 ≥2 个店铺品牌词）
brand_words = set()
for v in groups.values():
    brand_words |= v["brands"]
brand_words = {b for b in brand_words if len(b) >= 3}
print(f"\n店铺 SKU 品牌词 {len(brand_words)} 个: {sorted(brand_words)[:30]}")

svc = CsShopifySyncService()
cat = svc.load_cs_catalog()
diff = svc.diff(1, sample=4000)
cands = []
for it in diff["plan"]["to_create"]["items"]:
    row = cat.get(it["cs_id"]) or {}
    fm = row.get("fit_model", "")
    hits = sorted({b for b in brand_words if re.search(b, fm, re.I)})
    if len(hits) >= 2:
        cands.append((it["cs_id"], row.get("brand"), hits, fm[:120]))
print(f"\nto_create 多品牌候选 {len(cands)} 个，前 5:")
for c in cands[:5]:
    print(" ", c)
