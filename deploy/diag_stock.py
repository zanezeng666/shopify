# -*- coding: utf-8 -*-
"""单 SKU 库存同步链路诊断。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import session_scope, get_cs_engine
from shopify_admin.services.inventory.service import InventoryService

svc = InventoryService()
sku = "CS-CNR300VX_DeLonghi_77_0"

# 1) 镜像变体与 inventory_item_id
with session_scope() as s:
    row = s.execute(text(
        "SELECT pv.id, pv.sku, pv.inventory_item_id, pv.shopify_variant_id "
        "FROM product_variants pv WHERE pv.store_id=1 AND pv.sku=:k LIMIT 1"),
        {"k": sku}).one_or_none()
print("1) 变体镜像:", row)
if row is None or row[2] is None:
    print("   -> 变体缺失或无 inventory_item_id，诊断终止")
    sys.exit(0)

# 2) 渠道库存
with get_cs_engine().connect() as c:
    q = c.execute(text(
        "SELECT location, quantity FROM cs_inventory WHERE cs_id='CS-CNR300VX'")).all()
print("2) CS 库存:", q)

# 3) 策略目标值
tgt = svc._compute_target(1, sku, 30)
print("3) _compute_target(available=30) =", tgt)

# 4) 主位置
loc = svc.get_primary_location(1)
print("4) 主位置:", loc.location_id if loc else None)

# 5) 实推一次
r = svc.apply_channel_stock(1, [{"sku": sku, "available": 30, "cs_id": "CS-CNR300VX", "channel": "cs"}])
print("5) apply:", r.checked, r.updated, r.failed)

# 6) 日志表
with session_scope() as s:
    rows = s.execute(text(
        "SELECT sku, old_qty, new_qty, success, LEFT(message,150), created_at "
        "FROM inventory_sync_logs WHERE sku=:k ORDER BY id DESC LIMIT 3"),
        {"k": sku}).all()
print("6) 日志:", rows)
