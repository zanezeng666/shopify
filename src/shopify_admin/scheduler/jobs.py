# -*- coding: utf-8 -*-
"""定时任务（APScheduler 进程内托管，替代老系统 OS cron）。

任务清单（全部挂 @task_record 审计，写 task_result + 失败告警邮件）：
- pull_orders    拉单（可用店铺，Shopify 增量游标）
- auto_fulfill   自动履约：pending 订单分仓路由；SCHEDULER_AUTO_SUBMIT=true 才自动下单
- poll_channels  渠道状态轮询 + 跟踪号自动回传 Shopify
- sync_inventory 渠道库存 -> Shopify（CS/FastRite 本地镜像批量 + diff 预筛 + 单轮限流）
- daily_report   每店铺昨日销量汇总
- recalc_prices 定价引擎全量重算（20%/15%/亚马逊封顶）+ 改价 + 停售下架

手动触发：POST /tasks/{job}/run（REST），或 python -m shopify_admin.scheduler 独立跑调度进程。
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Callable

from loguru import logger
from sqlalchemy import func, or_, select, text

from shopify_admin.config.settings import settings
from shopify_admin.core.database import get_cs_engine, get_fastrite_engine, session_scope
from shopify_admin.core.task import task_record
from shopify_admin.models.order import Order
from shopify_admin.models.product import ProductVariant
from shopify_admin.services.fulfillment.service import FulfillmentService
from shopify_admin.services.inventory.service import InventoryService
from shopify_admin.services.orders.service import OrderService
from shopify_admin.services.reports.service import ReportService
from shopify_admin.services.stores.service import StoreService

# 变体 SKU -> 渠道商品锚点：'CS-MTB400SL_Motorola_69_0' -> 'CS-MTB400SL'
_CS_ID_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")


# ==================================================================
# 1. 拉单
# ==================================================================
@task_record
def job_pull_orders() -> str:
    parts: list[str] = []
    for st in StoreService().list_stores(available_only=True):
        r = OrderService().sync_orders(st["id"])
        parts.append(f"store{st['id']}: fetched={r.fetched} +{r.created} ~{r.updated}")
    return "; ".join(parts) or "no available stores"


# ==================================================================
# 2. 自动履约（分仓路由；默认不自动下单）
# ==================================================================
@task_record
def job_auto_fulfill() -> str:
    auto_submit = settings.scheduler_auto_submit
    # 只处理 Shopify 同步进来的新单：legacy 迁移单 raw 带 {"legacy": true} 标记，人工处理
    legacy_key = func.json_extract(Order.raw, "$.legacy")
    with session_scope() as s:
        ids = [
            r[0] for r in s.execute(
                select(Order.id)
                .where(
                    Order.local_status == "pending",
                    or_(Order.raw.is_(None), legacy_key.is_(None)),
                )
                .order_by(Order.id)
                .limit(200)
            )
        ]
    if not ids:
        return "pending=0"

    svc = FulfillmentService()
    routed = submitted = failed = 0
    for oid in ids:
        try:
            svc.route_order(oid)
            routed += 1
            if auto_submit:
                svc.submit_order(oid)
                submitted += 1
        except Exception as e:  # 单单失败不阻断整批
            failed += 1
            logger.warning(f"[auto_fulfill] 订单 {oid} 失败: {e}")
    return (
        f"pending={len(ids)} routed={routed} submitted={submitted} "
        f"failed={failed} auto_submit={auto_submit}"
    )


# ==================================================================
# 3. 渠道状态轮询 + 跟踪号回传
# ==================================================================
@task_record
def job_poll_channels() -> str:
    r = FulfillmentService().poll_channel_status()
    return str(r)


# ==================================================================
# 4. 库存同步（渠道镜像 -> Shopify）
# ==================================================================
def _load_cs_mirror() -> dict[str, int]:
    """CS 库存镜像（bmai cs_new.cs_inventory）：cs_id -> 总可用。"""
    with get_cs_engine().connect() as c:
        rows = c.execute(
            text("SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id")
        ).all()
    return {str(r[0]).strip(): int(r[1] or 0) for r in rows if r[0]}


def _load_fr_mirror() -> dict[str, int]:
    """FastRite 库存镜像（fast_rite.stock_table）：cs_id -> 可用总量（多仓求和）。"""
    with get_fastrite_engine().connect() as c:
        rows = c.execute(
            text(
                "SELECT cs_id, SUM(productStockDtl_availableAmount) FROM stock_table "
                "WHERE cs_id IS NOT NULL AND cs_id != '' GROUP BY cs_id"
            )
        ).all()
    return {str(r[0]).strip(): int(r[1] or 0) for r in rows if r[0]}


@task_record
def job_sync_inventory() -> str:
    cs_mirror = _load_cs_mirror()
    fr_mirror = _load_fr_mirror()
    fr_ids = set(fr_mirror)
    cap = settings.scheduler_inventory_max_per_run
    parts: list[str] = []
    for st in StoreService().list_stores(available_only=True):
        sid = st["id"]
        with session_scope() as s:
            skus = [
                (r[0] or "").strip()
                for r in s.execute(select(ProductVariant.sku).where(ProductVariant.store_id == sid))
            ]
        cs_stocks: list[dict] = []
        fr_stocks: list[dict] = []
        for sku in skus:
            m = _CS_ID_RE.match(sku)
            if not m:
                continue
            csid = m.group(1)
            if csid in fr_ids:
                fr_stocks.append({"sku": sku, "cs_id": csid, "available": fr_mirror[csid], "channel": "fastrite"})
            elif csid in cs_mirror:
                cs_stocks.append({"sku": sku, "cs_id": csid, "available": cs_mirror[csid], "channel": "cs"})
        inv = InventoryService()
        segs: list[str] = []
        for label, stocks in (("cs", cs_stocks), ("fastrite", fr_stocks)):
            if not stocks:
                segs.append(f"{label}: none")
                continue
            diff = inv.diff_channel_stock(sid, stocks)
            todo = diff["changed"][:cap]
            if not todo:
                segs.append(f"{label}: 0 push (match={len(stocks)} unchanged={diff['unchanged']})")
                continue
            r = inv.apply_channel_stock(sid, todo)
            segs.append(
                f"{label}: match={len(stocks)} changed={len(diff['changed'])} "
                f"pushed={r.updated} failed={r.failed} cap={cap}"
            )
        parts.append(f"store{sid} " + " | ".join(segs))
    return "; ".join(parts) or "no available stores"


# ==================================================================
# 5. 日报
# ==================================================================
@task_record
def job_daily_report() -> str:
    day = date.today() - timedelta(days=1)
    ds = day.strftime("%Y-%m-%d")
    parts = []
    for st in StoreService().list_stores(available_only=True):
        rows = ReportService().sales_report(st["id"], ds, ds)
        qty = sum(int(r.get("quantity") or 0) for r in rows)
        parts.append(f"store{st['id']}: {len(rows)} 款 / {qty} 件")
    return f"{ds} " + "; ".join(parts)


# ==================================================================
# 6. 产品周同步（CS 产品库 → Shopify：发布新品 + 条码补空/重量对齐）
# ==================================================================
@task_record
def job_sync_products() -> str:
    """每周：刷新 CS 产品镜像 → 各店对账执行。

    价格默认 report-only（实证店铺为独立零售定价体系，99.8% 与 CS 建议零售价不同）；
    新品发布形态/每轮上限由 settings 控制，条码冲突跳过、营销字段永不覆盖。
    """
    from shopify_admin.services.products.sync_shopify import CsShopifySyncService

    svc = CsShopifySyncService()
    stores = StoreService().list_stores(available_only=True)
    # cs_product 是全局镜像：任一店铺 rcustomerno 刷一次即可（失败降级用现有镜像）
    rno = next((st["rcustomerno"] for st in stores if st.get("rcustomerno")), settings.bmai_rcustomerno)
    if rno:
        try:
            svc.refresh_cs_catalog(rno)
        except Exception as e:
            logger.warning(f"[sync_products] CS 镜像刷新失败，降级用现有镜像: {e}")
    parts: list[str] = []
    for st in stores:
        try:
            r = svc.apply(
                st["id"],
                dry_run=False,
                price_mode=settings.scheduler_product_sync_price_mode,
                publish_status=settings.scheduler_product_sync_publish,
                max_ops=settings.scheduler_product_sync_max_ops,
            )
            parts.append(
                f"store{st['id']}: +{r['created']} ~{r['updated']} "
                f"skip={r['skipped_existing']} fail={r['failed']}"
            )
        except Exception as e:  # 单店失败不阻断
            parts.append(f"store{st['id']}: ERROR {str(e)[:120]}")
            logger.warning(f"[sync_products] store{st['id']} 失败: {e}")
    return "; ".join(parts) or "no available stores"


# ==================================================================
# 7. 定价引擎（成本+运费+平台费 → 全量重定价 + 停售下架，2026-11-04 规则）
# ==================================================================
@task_record
def job_recalc_prices() -> str:
    """每日：全量定价决策（20% 标准 / 15% 底线 / 亚马逊参考价封顶）→ 各店改价 + 停售下架。

    规则定稿见 services/pricing/service.py 模块注释；改价每轮限量（限流收敛，
    余量次日消化，手动可反复触发）。
    """
    from shopify_admin.services.pricing import PricingService

    stats = PricingService().run_all_stores(dry_run=False)
    d = stats["decisions"]
    parts = [
        f"priced={d['priced']}/{d['total']} stopped={d['stopped']} "
        f"no_cost={d['no_cost']} margin_risk={d['margin_risk']} "
        f"basis[a20/cap/f15]={d['basis']['formula20']}/{d['basis']['amazon_cap']}/{d['basis']['floor15']}"
    ]
    for st in stats["stores"]:
        if "error" in st:
            parts.append(f"store{st['store_id']}: ERROR {st['error'][:80]}")
            continue
        r, dl = st["recalc"], st["delist"]
        parts.append(
            f"store{st['store_id']}: price {r['updated']}/{r['to_update']}↑"
            f" fail={r['failed']} defer={r.get('deferred', 0)} | delist {dl['delisted']}/{dl['to_delist']}"
        )
    return "; ".join(parts)


# ==================================================================
# 注册表（手动触发端点共用）
# ==================================================================
JOBS: dict[str, Callable[[], str]] = {
    "pull_orders": job_pull_orders,
    "auto_fulfill": job_auto_fulfill,
    "poll_channels": job_poll_channels,
    "sync_inventory": job_sync_inventory,
    "daily_report": job_daily_report,
    "sync_products": job_sync_products,
    "recalc_prices": job_recalc_prices,
}

JOB_CRONS: dict[str, str] = {
    "pull_orders": settings.scheduler_pull_orders_cron,
    "auto_fulfill": settings.scheduler_fulfill_cron,
    "poll_channels": settings.scheduler_channel_poll_cron,
    "sync_inventory": settings.scheduler_inventory_sync_cron,
    "daily_report": settings.scheduler_reports_cron,
    "sync_products": settings.scheduler_product_sync_cron,
    "recalc_prices": settings.scheduler_price_recalc_cron,
}
