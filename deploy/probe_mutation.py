# -*- coding: utf-8 -*-
"""复现跑批第一个 mutation：dry_run 拿 todo → 按产品分组 → 真发第一个产品（与 service.py:439 同构）"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="WARNING")

from sqlalchemy import select
from shopify_admin.services.pricing import PricingService
from shopify_admin.core.database import session_scope
from shopify_admin.models import ProductVariant

svc = PricingService()
t0 = time.time()
decisions = svc.build_decisions()
print(f"build_decisions: {time.time()-t0:.1f}s, n={len(decisions)}")

t0 = time.time()
r = svc.recalc_store(1, decisions, dry_run=True)
print(f"dry_run diff: {time.time()-t0:.1f}s -> {r}")

# 与 _push_price_updates_graphql 相同的分组
todo = []
for vid, sku, cur in svc._variant_cs_ids(1):
    from shopify_admin.services.pricing.service import _CS_ID_RE
    m = _CS_ID_RE.match(sku)
    if not m:
        continue
    d = decisions.get(m.group(1))
    if d is None or d.stopped or d.price is None:
        continue
    if cur is not None and abs(float(cur) - d.price) < 0.005:
        continue
    todo.append((vid, sku, d.price))

with session_scope() as s:
    rows = s.execute(
        select(ProductVariant.shopify_variant_id, ProductVariant.shopify_product_id)
        .where(ProductVariant.store_id == 1)).all()
vid2pid = {r0[0]: r0[1] for r0 in rows}
by_prod = {}
for vid, _sku, price in todo:
    pid = vid2pid.get(vid)
    if pid:
        by_prod.setdefault(pid, []).append((vid, price))

sizes = sorted((len(v) for v in by_prod.values()), reverse=True)
print(f"todo={len(todo)} products={len(by_prod)} top_variant_counts={sizes[:5]}")

# 真发第一个产品（与跑批完全同构）
client = svc._stores.get_client(1)
pid0, items0 = next(iter(by_prod.items()))
vinput = [{"id": f"gid://shopify/ProductVariant/{v}", "price": f"{p:.2f}"} for v, p in items0]
print(f"first product {pid0}: {len(items0)} variants, payload={len(str(vinput))} chars")
t0 = time.time()
try:
    data = client.graphql(svc._BULK_PRICE_MUTATION, {"pid": f"gid://shopify/Product/{pid0}", "vs": vinput})
    print(f"OK elapsed={time.time()-t0:.2f}s -> {str(data)[:200]}")
except Exception as e:
    print(f"EXC elapsed={time.time()-t0:.2f}s {type(e).__name__}: {str(e)[:300]}")
client.close()
