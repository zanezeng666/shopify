# -*- coding: utf-8 -*-
"""财务服务：payout 同步 / 交易流水同步 / 订单成本核算 / 利润汇总。"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, select

from shopify_admin.core.database import session_scope
from shopify_admin.models.finance import OrderCost, Payout, Transaction
from shopify_admin.models.order import Order, OrderItem
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService


def _to_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _dec(value):
    if value in (None, ""):
        return None
    return Decimal(str(value))


class FinanceService:
    def __init__(self, store_service: StoreService | None = None):
        self._stores = store_service or StoreService()

    # ------------------------------------------------------------------
    def sync_payouts(self, store_id: int, max_pages: int = 5) -> dict:
        client = self._stores.get_client(store_id)
        try:
            rest = ShopifyRest(client)
            page = n_new = 0
            page_info = None
            while page < max_pages:
                payouts = rest.payouts(page_info=page_info)
                if not payouts:
                    break
                for p in payouts:
                    with session_scope() as s:
                        row = s.execute(
                            select(Payout).where(Payout.store_id == store_id, Payout.payout_id == p["id"])
                        ).scalar_one_or_none()
                        if row is None:
                            row = Payout(store_id=store_id, payout_id=p["id"])
                            s.add(row)
                            n_new += 1
                        row.status = p.get("status") or ""
                        row.payout_date = _to_dt(p.get("date"))
                        row.currency = p.get("currency") or ""
                        row.amount = _dec(p.get("amount"))
                        row.fee = _dec(p.get("fee"))
                        row.net_amount = _dec(p.get("net_amount"))
                        row.raw = p
                if len(payouts) < 250:
                    break
                page += 1
            return {"payouts_new": n_new}
        finally:
            client.close()

    def sync_transactions(self, store_id: int, order_id: int | None = None, max_pages: int = 5) -> dict:
        """同步交易流水。order_id 给定时同步单订单交易，否则全量（since_id 增量）。"""
        client = self._stores.get_client(store_id)
        try:
            rest = ShopifyRest(client)
            n_new = 0
            if order_id is not None:
                txns = rest.transactions(order_id)
                for t in txns:
                    n_new += self._upsert_txn(store_id, t)
            else:
                with session_scope() as s:
                    since = s.execute(
                        select(func.max(Transaction.transaction_id)).where(Transaction.store_id == store_id)
                    ).scalar() or 0
                for _ in range(max_pages):
                    txns = rest.all_transactions(since_id=since or None)
                    if not txns:
                        break
                    for t in txns:
                        n_new += self._upsert_txn(store_id, t)
                    if len(txns) < 250:
                        break
                    since = txns[-1]["id"]
            return {"transactions_new": n_new}
        finally:
            client.close()

    @staticmethod
    def _upsert_txn(store_id: int, t: dict) -> int:
        with session_scope() as s:
            row = s.execute(
                select(Transaction).where(Transaction.store_id == store_id, Transaction.transaction_id == t["id"])
            ).scalar_one_or_none()
            if row is None:
                row = Transaction(store_id=store_id, transaction_id=t["id"])
                s.add(row)
                is_new = 1
            else:
                is_new = 0
            row.shopify_order_id = t.get("order_id")
            row.kind = t.get("kind") or ""
            row.gateway = t.get("gateway") or ""
            row.status = t.get("status") or ""
            row.currency = t.get("currency") or ""
            row.amount = _dec(t.get("amount"))
            row.fee = _dec(t.get("fee"))
            row.net = _dec(t.get("net"))
            row.processed_at = _to_dt(t.get("processed_at"))
            row.raw = t
            return is_new

    # ------------------------------------------------------------------
    def calc_order_cost(self, order_id: int) -> dict:
        """订单成本核算：收入（订单行项）- 货品成本/运费（履约单记录）→ order_costs。

        渠道成本来源：fulfillment_orders.raw 中渠道返回的报价明细（CS 下单响应 / FastRite 费用）。
        """
        from shopify_admin.models.fulfillment import FulfillmentOrder

        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                from shopify_admin.core.exceptions import NotFoundError

                raise NotFoundError(f"订单不存在: {order_id}")
            items = s.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
            fos = s.execute(
                select(FulfillmentOrder).where(FulfillmentOrder.order_id == order_id)
            ).scalars().all()

            rows = []
            for it in items:
                # 找对应行项的履约单成本
                fo = next((f for f in fos if f.order_item_id == it.id), None)
                cost_detail = (fo.raw or {}) if fo else {}
                product_cost = _dec(cost_detail.get("product_cost") or cost_detail.get("total_price"))
                shipping_cost = _dec(cost_detail.get("shipping_cost") or cost_detail.get("freight"))
                best_shipping = _dec(cost_detail.get("best_shipping_cost"))
                revenue = (it.price or Decimal("0")) * it.quantity - (it.total_discount or Decimal("0"))
                profit = None
                if revenue is not None and product_cost is not None:
                    profit = revenue - product_cost - (shipping_cost or Decimal("0"))

                row = s.execute(
                    select(OrderCost).where(OrderCost.order_id == order_id, OrderCost.sku == it.sku)
                ).scalar_one_or_none()
                if row is None:
                    row = OrderCost(order_id=order_id, store_id=order.store_id, sku=it.sku)
                    s.add(row)
                row.cs_id = it.cs_id or (fo.channel if fo else "")
                row.channel = fo.channel if fo else order.channel
                row.quantity = it.quantity
                row.currency = order.currency
                row.revenue = revenue
                row.product_cost = product_cost
                row.shipping_cost = shipping_cost
                row.best_shipping_cost = best_shipping
                row.profit = profit
                row.detail = cost_detail
                rows.append({"sku": it.sku, "revenue": float(revenue), "profit": float(profit) if profit is not None else None})
            return {"order_id": order_id, "items": rows}

    # ------------------------------------------------------------------
    def list_payouts(self, store_id: int, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        with session_scope() as s:
            stmt = select(Payout).where(Payout.store_id == store_id)
            count_stmt = select(func.count(Payout.id)).where(Payout.store_id == store_id)
            if status:
                stmt = stmt.where(Payout.status == status)
                count_stmt = count_stmt.where(Payout.status == status)
            total = s.execute(count_stmt).scalar() or 0
            rows = (
                s.execute(stmt.order_by(Payout.payout_date.desc()).offset((page - 1) * page_size).limit(page_size))
                .scalars()
                .all()
            )
            return {
                "total": total,
                "items": [
                    {
                        "id": r.id, "payout_id": r.payout_id, "status": r.status,
                        "payout_date": r.payout_date.isoformat() if r.payout_date else None,
                        "currency": r.currency,
                        "amount": float(r.amount) if r.amount is not None else None,
                        "fee": float(r.fee) if r.fee is not None else None,
                        "net_amount": float(r.net_amount) if r.net_amount is not None else None,
                    }
                    for r in rows
                ],
            }

    def list_transactions(self, store_id: int, kind: str | None = None, page: int = 1, page_size: int = 50) -> dict:
        with session_scope() as s:
            stmt = select(Transaction).where(Transaction.store_id == store_id)
            count_stmt = select(func.count(Transaction.id)).where(Transaction.store_id == store_id)
            if kind:
                stmt = stmt.where(Transaction.kind == kind)
                count_stmt = count_stmt.where(Transaction.kind == kind)
            total = s.execute(count_stmt).scalar() or 0
            rows = (
                s.execute(
                    stmt.order_by(Transaction.processed_at.desc()).offset((page - 1) * page_size).limit(page_size)
                )
                .scalars()
                .all()
            )
            return {
                "total": total,
                "items": [
                    {
                        "id": r.id, "transaction_id": r.transaction_id,
                        "shopify_order_id": r.shopify_order_id, "kind": r.kind,
                        "gateway": r.gateway, "status": r.status, "currency": r.currency,
                        "amount": float(r.amount) if r.amount is not None else None,
                        "fee": float(r.fee) if r.fee is not None else None,
                        "net": float(r.net) if r.net is not None else None,
                        "processed_at": r.processed_at.isoformat() if r.processed_at else None,
                    }
                    for r in rows
                ],
            }

    # ------------------------------------------------------------------
    def summary(self, store_id: int, date_from: str | None = None, date_to: str | None = None) -> dict:
        """利润汇总：订单收入 + 成本 + 平台净入账。"""
        with session_scope() as s:
            stmt = select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_price), 0),
            ).where(Order.store_id == store_id, Order.is_test.is_(False))
            if date_from:
                stmt = stmt.where(Order.shopify_created_at >= _to_dt(date_from))
            if date_to:
                stmt = stmt.where(Order.shopify_created_at <= _to_dt(date_to))
            order_count, revenue = s.execute(stmt).one()

            cost_stmt = select(
                func.coalesce(func.sum(OrderCost.revenue), 0),
                func.coalesce(func.sum(OrderCost.product_cost), 0),
                func.coalesce(func.sum(OrderCost.shipping_cost), 0),
                func.coalesce(func.sum(OrderCost.profit), 0),
            ).where(OrderCost.store_id == store_id)
            if date_from:
                cost_stmt = cost_stmt.where(OrderCost.created_at >= _to_dt(date_from))
            if date_to:
                cost_stmt = cost_stmt.where(OrderCost.created_at <= _to_dt(date_to))
            rev2, prod_cost, ship_cost, profit = s.execute(cost_stmt).one()

            payout_stmt = select(
                func.count(Payout.id), func.coalesce(func.sum(Payout.net_amount), 0)
            ).where(Payout.store_id == store_id, Payout.status == "paid")
            payout_count, payout_net = s.execute(payout_stmt).one()

            return {
                "store_id": store_id,
                "orders": order_count,
                "order_revenue": float(revenue or 0),
                "cost_revenue": float(rev2 or 0),
                "product_cost": float(prod_cost or 0),
                "shipping_cost": float(ship_cost or 0),
                "profit": float(profit or 0),
                "payouts": payout_count,
                "payout_net": float(payout_net or 0),
            }
