# -*- coding: utf-8 -*-
"""从镜像随机抽 3 个今日新品验证在线库存。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

with session_scope() as s:
    rows = s.execute(text(
        "SELECT p.handle, pv.sku FROM products p "
        "JOIN product_variants pv ON pv.product_id = p.id "
        "WHERE p.store_id=1 AND p.status='active' "
        "AND p.created_at >= '2026-11-04 19:50:00' "
        "ORDER BY p.id DESC LIMIT 3")).all()

c = ShopifyRest(StoreService().get_client(1)).client
q = '{ productByHandle(handle: "%s") { status variants(first:1) { nodes { sku inventoryQuantity } } } }'
for handle, sku in rows:
    r = c.graphql(q % handle)
    p = r["productByHandle"] or {}
    v = (p.get("variants", {}).get("nodes") or [{}])[0]
    ok = "OK" if (p.get("status") == "ACTIVE" and v.get("sku") == sku) else "MISMATCH"
    print(f"{ok} {sku} 线上qty={v.get('inventoryQuantity')}")
