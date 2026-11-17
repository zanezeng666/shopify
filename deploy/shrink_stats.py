# -*- coding: utf-8 -*-
"""索引抢救 step1：URL 收缩候选统计 v3（纯只读）。

v3 关键修正：本地镜像 status 失真（25,965 行标 active，远端实际 active=12,201），
全部统计改为以 Shopify 远端实测 active 产品 id 为基数。

档位定义（命中即保留）：
  A 精锐: medical ∪ (有货 ∩ 有亚马逊价)
  B 平衡: A ∪ 有历史销量
  C 保守: medical ∪ 有货
"""
from __future__ import annotations

import json
import re
import time

from sqlalchemy import select, text

from shopify_admin.core.database import get_cs_engine, session_scope
from shopify_admin.models.order import OrderItem
from shopify_admin.models.product import Product, ProductVariant

_CS_ID_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")
OUT_IDS = "/home/jason/shopify-admin/deploy/shrink_draft_ids.json"


def remote_active_ids() -> list[int]:
    from shopify_admin.services.stores.service import StoreService

    client = StoreService().get_client(1)
    ids: list[int] = []
    since = 0
    try:
        while True:
            params = {"limit": 250, "status": "active", "since_id": since, "fields": "id"}
            batch = client.request("GET", "products.json", params=params).get("products", [])
            if not batch:
                break
            ids.extend(int(p["id"]) for p in batch)
            since = ids[-1]
            time.sleep(0.35)   # ~2.8 req/s，防 429
    finally:
        client.close()
    return ids


def main() -> None:
    rids = remote_active_ids()
    print(f"远端实测 active 产品: {len(rids)}")
    rid_set = set(rids)

    # 本地映射：远端 active id -> (tags, product_type, cs_ids)
    with session_scope() as s:
        rows = s.execute(
            select(Product.shopify_product_id, Product.tags, Product.product_type, ProductVariant.sku)
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .where(Product.store_id == 1, Product.shopify_product_id.in_(rid_set))
        ).all()
    prod: dict[int, dict] = {}
    for pid, tags, ptype, sku in rows:
        p = prod.setdefault(int(pid), {"tags": tags or "", "ptype": ptype or "", "cs": set()})
        m = _CS_ID_RE.match((sku or "").strip())
        if m:
            p["cs"].add(m.group(1))
    print(f"本地可映射: {len(prod)}（镜像缺行 {len(rid_set - set(prod))}）")

    with get_cs_engine().connect() as c:
        inv = c.execute(text(
            "SELECT DISTINCT cs_id FROM cs_inventory "
            "WHERE location IN ('US','SZ','HK') AND quantity > 0"
        )).all()
    has_stock = {str(r[0]).strip() for r in inv if r[0]}

    with get_cs_engine().connect() as c:
        amz = c.execute(text(
            "SELECT DISTINCT cs_id FROM amazon.amazon_inventory "
            "WHERE cs_id IS NOT NULL AND cs_id <> '' AND market_id = 'ATVPDKIKX0DER' "
            "AND price IS NOT NULL AND price <> ''"
        )).all()
    has_amzn = {str(r[0]).strip() for r in amz if r[0]}

    with session_scope() as s:
        sold = s.execute(
            select(OrderItem.cs_id).where(OrderItem.cs_id.is_not(None), OrderItem.cs_id != "")
        ).all()
    sold_cs = {str(r[0]).strip() for r in sold}

    total = len(prod)
    stats = {"med": 0, "stock": 0, "amzn": 0, "sold": 0, "stock_amzn": 0, "med_nostock": 0}
    plan: dict[str, list[int]] = {"A": [], "B": [], "C": []}
    for pid, p in prod.items():
        is_med = "ad-medical" in p["tags"] or "medical" in p["ptype"].lower()
        stock = bool(p["cs"] & has_stock)
        amzn = bool(p["cs"] & has_amzn)
        sold_ = bool(p["cs"] & sold_cs)
        if is_med:
            stats["med"] += 1
            if not stock:
                stats["med_nostock"] += 1
        if stock:
            stats["stock"] += 1
        if amzn:
            stats["amzn"] += 1
        if sold_:
            stats["sold"] += 1
        if stock and amzn:
            stats["stock_amzn"] += 1
        if is_med or (stock and amzn):
            plan["A"].append(pid)
        if is_med or (stock and amzn) or sold_:
            plan["B"].append(pid)
        if is_med or stock:
            plan["C"].append(pid)

    print(f"真基数分层: medical={stats['med']}(无货{stats['med_nostock']}) 有货={stats['stock']} "
          f"有价={stats['amzn']} 有销量={stats['sold']} 有货∩有价={stats['stock_amzn']}")
    for k in ("A", "B", "C"):
        keep = len(plan[k])
        print(f"档位{k}: 保留 {keep} ({keep * 100.0 / total:.1f}%) → 转 DRAFT {total - keep}")

    with open(OUT_IDS, "w", encoding="utf-8") as f:
        json.dump({
            "base_total": total,
            "keepA": plan["A"], "keepB": plan["B"], "keepC": plan["C"],
            "draftA": sorted(set(prod) - set(plan["A"])),
            "draftB": sorted(set(prod) - set(plan["B"])),
            "draftC": sorted(set(prod) - set(plan["C"])),
        }, f)
    print(f"-> {OUT_IDS}（各档保留/候选清单，未执行任何写操作）")


if __name__ == "__main__":
    main()
