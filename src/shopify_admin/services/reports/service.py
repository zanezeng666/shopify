# -*- coding: utf-8 -*-
"""报表服务：本地库 SQL 聚合（销量/订单/库存）。大数据量走 GraphQL bulk（platforms.shopify.graphql）。"""
from __future__ import annotations

from sqlalchemy import case, func, select

from shopify_admin.core.database import session_scope
from shopify_admin.models.inventory import InventoryLevel
from shopify_admin.models.order import Order, OrderItem


def _to_dt(value):
    from datetime import datetime

    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


class ReportService:
    def sales_report(
        self,
        store_id: int,
        date_from: str | None = None,
        date_to: str | None = None,
        by: str = "sku",
    ) -> list[dict]:
        """销量报表（按 SKU / 按日）。by: sku | day"""
        with session_scope() as s:
            stmt = (
                select(OrderItem.sku, func.sum(OrderItem.quantity), func.count(func.distinct(Order.id)))
                .join(Order, Order.id == OrderItem.order_id)
                .where(Order.store_id == store_id, Order.is_test.is_(False))
            )
            if by == "day":
                day = func.date(Order.shopify_created_at)
                stmt = (
                    select(day, func.sum(OrderItem.quantity), func.count(func.distinct(Order.id)))
                    .join(Order, Order.id == OrderItem.order_id)
                    .where(Order.store_id == store_id, Order.is_test.is_(False))
                    .group_by(day)
                    .order_by(day)
                )
            else:
                stmt = stmt.group_by(OrderItem.sku).order_by(func.sum(OrderItem.quantity).desc())
            if date_from:
                stmt = stmt.where(Order.shopify_created_at >= _to_dt(date_from))
            if date_to:
                stmt = stmt.where(Order.shopify_created_at <= _to_dt(date_to))
            rows = s.execute(stmt).all()
            key = "day" if by == "day" else "sku"
            return [
                {key: str(r[0]), "quantity": int(r[1] or 0), "orders": int(r[2] or 0)} for r in rows
            ]

    def order_status_report(self, store_id: int) -> dict:
        """订单状态分布（本系统状态机 + Shopify 财务状态）。"""
        with session_scope() as s:
            local = s.execute(
                select(Order.local_status, func.count(Order.id))
                .where(Order.store_id == store_id)
                .group_by(Order.local_status)
            ).all()
            financial = s.execute(
                select(Order.financial_status, func.count(Order.id))
                .where(Order.store_id == store_id)
                .group_by(Order.financial_status)
            ).all()
            return {
                "local_status": {k or "pending": int(v) for k, v in local},
                "financial_status": {k or "(空)": int(v) for k, v in financial},
            }

    def inventory_report(self, store_id: int, low_threshold: int = 5) -> dict:
        with session_scope() as s:
            total = s.execute(
                select(func.count(InventoryLevel.id)).where(InventoryLevel.store_id == store_id)
            ).scalar() or 0
            zero = s.execute(
                select(func.count(InventoryLevel.id)).where(
                    InventoryLevel.store_id == store_id, InventoryLevel.available <= 0
                )
            ).scalar() or 0
            low = s.execute(
                select(func.count(InventoryLevel.id)).where(
                    InventoryLevel.store_id == store_id,
                    InventoryLevel.available > 0,
                    InventoryLevel.available <= low_threshold,
                )
            ).scalar() or 0
            return {"total_skus": total, "zero": zero, f"low(<={low_threshold})": low}
