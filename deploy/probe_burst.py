# -*- coding: utf-8 -*-
"""连续 50 个真实 mutation，观测速率惩罚拐点（幂等：价格=决策价）"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="WARNING")

from sqlalchemy import select
from shopify_admin.services.pricing import PricingService
from shopify_admin.services.pricing.service import _CS_ID_RE
from shopify_admin.core.database import session_scope
from shopify_admin.models import ProductVariant

svc = PricingService()
decisions = svc.build_decisions()

todo = []
for vid, sku, cur in svc._variant_cs_ids(1):
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

client = svc._stores.get_client(1)
items = list(by_prod.items())[:50]
print(f"发送 {len(items)} 个产品 mutation，无间隔连发")
t_start = time.time()
slow_at = None
for i, (pid, vs) in enumerate(items):
    vinput = [{"id": f"gid://shopify/ProductVariant/{v}", "price": f"{p:.2f}"} for v, p in vs]
    t0 = time.time()
    try:
        data = client.graphql(svc._BULK_PRICE_MUTATION, {"pid": f"gid://shopify/Product/{pid}", "vs": vinput})
        dt = time.time() - t0
        ue = (data.get("productVariantsBulkUpdate", {}).get("userErrors")) or []
        flag = "UE" if ue else "ok"
        print(f"[{i+1:3d}] {dt:6.2f}s {flag} pid={pid} {'|'.join(str(u.get('message'))[:40] for u in ue[:1])}")
        if dt > 5 and slow_at is None:
            slow_at = i + 1
            print(f"    ^^^ 拐点：第 {slow_at} 个开始变慢")
    except Exception as e:
        dt = time.time() - t0
        print(f"[{i+1:3d}] {dt:6.2f}s EXC {type(e).__name__}: {str(e)[:120]}")
        if slow_at is None:
            slow_at = i + 1
            print(f"    ^^^ 拐点：第 {slow_at} 个出错")
print(f"总耗时 {time.time()-t_start:.1f}s，拐点={slow_at}")
client.close()
