# -*- coding: utf-8 -*-
"""给本轮新建产品批量补渠道库存水位（走 InventoryService.apply_channel_stock 系统链路）。

圈定：/tmp/launch_done.txt 的 cs_id ↔ 镜像变体 SKU（CS- 前缀锚定）。
水位：cs_inventory 按仓聚合（与 CsChannel.get_inventory 同源）。
用法：python backfill_stock.py [试推N，缺省全量]
"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from loguru import logger
from sqlalchemy import text

from shopify_admin.core.database import session_scope, get_cs_engine
from shopify_admin.services.inventory.service import InventoryService

logger.remove()
logger.add(sys.stderr, level="INFO")

CS_RE = re.compile(r"^CS-([A-Z0-9]+)_")
LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 0

done = {x.strip() for x in open("/tmp/launch_done.txt").read().split() if x.strip()}
logger.info(f"本轮新建 cs_id={len(done)}")

with get_cs_engine().connect() as c:
    inv = {r[0]: int(r[1] or 0) for r in c.execute(
        text("SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id")).all()}

stocks: list[dict] = []
miss_inv = 0
with session_scope() as s:
    rows = s.execute(text(
        "SELECT pv.sku FROM product_variants pv "
        "JOIN products p ON p.id = pv.product_id "
        "WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%' "
        "AND p.status = 'active' AND p.created_at >= '2026-11-04 19:50:00'")).all()
for (sku,) in rows:
    m = CS_RE.match(sku or "")
    if not m:
        continue
    csid = m.group(0)[:-1]  # 保留 CS- 前缀（launch_done 同口径）
    if csid not in done:
        continue
    q = inv.get(csid, 0)
    if q <= 0:
        miss_inv += 1
        continue
    stocks.append({"sku": sku, "available": q, "cs_id": csid, "channel": "cs"})
logger.info(f"待补水位 SKU={len(stocks)}（无库存跳过 {miss_inv}）")
if LIMIT:
    stocks = stocks[:LIMIT]
    logger.info(f"试推 {len(stocks)}")

svc = InventoryService()
r = svc.apply_channel_stock(1, stocks)
logger.info(f"RESULT checked={r.checked} updated={r.updated} "
            f"unchanged={r.unchanged} failed={r.failed}")
for msg in getattr(r, "messages", [])[:10]:
    logger.info(f"  MSG: {msg}")
