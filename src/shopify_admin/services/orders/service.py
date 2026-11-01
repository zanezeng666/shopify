# -*- coding: utf-8 -*-
"""订单服务：增量拉单 / 查询 / 确认 / 取消。

拉单策略：
- 游标 = 库内该店铺 max(shopify_created_at) 往前回退 30 分钟（重叠防漏单）
- created_at_min 增量 + page_info 翻页，upsert 落库
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shopify_admin.core.database import session_scope
from shopify_admin.core.exceptions import NotFoundError, ShopifyAPIError
from shopify_admin.models.order import Order, OrderItem
from shopify_admin.platforms.shopify.client import ShopifyClient
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.platforms.shopify.types import OrderSyncResult
from shopify_admin.services.stores.service import StoreService

# 拉单重叠窗口：覆盖 Shopify 侧创建延迟与漏单
_OVERLAP = timedelta(minutes=30)
_MAX_PAGES = 20


def _to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


class OrderService:
    def __init__(self, store_service: StoreService | None = None):
        self._stores = store_service or StoreService()

    # ------------------------------------------------------------------
    def sync_orders(
        self,
        store_id: int,
        created_at_min: str | None = None,
        max_pages: int = _MAX_PAGES,
        financial_status: str | None = None,
    ) -> OrderSyncResult:
        """增量拉单入库。created_at_min 显式传入时忽略自动游标。"""
        client = self._stores.get_client(store_id)
        rest = ShopifyRest(client)

        if created_at_min is None:
            with session_scope() as s:
                last = s.execute(
                    select(func.max(Order.shopify_created_at)).where(Order.store_id == store_id)
                ).scalar()
            if last is not None:
                created_at_min = (last - _OVERLAP).strftime("%Y-%m-%dT%H:%M:%S%z") or None

        fetched = created_n = updated_n = 0
        page = 0
        params: dict[str, Any] = {"limit": 250}
        if created_at_min:
            params["created_at_min"] = created_at_min
        if financial_status:
            params["financial_status"] = financial_status

        while page < max_pages:
            orders = rest.orders(**params)
            if not orders:
                break
            for o in orders:
                created, updated = self._upsert_order(s=None, store_id=store_id, payload=o)
                fetched += 1
                created_n += created
                updated_n += updated
            if len(orders) < 250:
                break
            params["since_id"] = orders[-1]["id"]
            page += 1

        result = OrderSyncResult(
            store_id=store_id, fetched=fetched, created=created_n, updated=updated_n,
        )
        logger.info(f"[orders] 拉单完成 store={store_id} {result.model_dump()}")
        client.close()
        return result

    # ------------------------------------------------------------------
    def _upsert_order(self, s: Session | None, store_id: int, payload: dict) -> tuple[int, int]:
        """单订单 upsert（orders + order_items）。s 传入时复用会话。"""
        ctx = _session_ctx(s)
        with ctx as sess:
            spid = payload["id"]
            order = sess.execute(
                select(Order).where(Order.store_id == store_id, Order.shopify_order_id == spid)
            ).scalar_one_or_none()
            is_new = order is None
            if is_new:
                order = Order(store_id=store_id, shopify_order_id=spid)
                sess.add(order)

            self._apply_fields(order, payload)
            self._upsert_items(sess, order, payload.get("line_items", []))
            return (1, 0) if is_new else (0, 1)

    @staticmethod
    def _apply_fields(order: Order, o: dict) -> None:
        order.name = o.get("name", "")
        order.order_number = o.get("order_number") or 0
        order.email = o.get("email") or o.get("contact_email") or ""
        order.phone = o.get("phone") or ""
        order.financial_status = o.get("financial_status") or ""
        order.fulfillment_status = o.get("fulfillment_status") or "unfulfilled"
        order.currency = o.get("currency") or ""
        order.total_price = _dec(o.get("total_price"))
        order.subtotal_price = _dec(o.get("subtotal_price"))
        order.total_tax = _dec(o.get("total_tax"))
        order.total_discounts = _dec(o.get("total_discounts"))
        order.shipping_price = _dec(o.get("total_shipping_price_set", {}).get("shop_money", {}).get("amount"))
        order.tags = o.get("tags") or ""
        order.note = o.get("note") or ""
        order.shipping_address = o.get("shipping_address")
        order.billing_address = o.get("billing_address")
        order.customer = o.get("customer")
        order.is_test = bool(o.get("test"))
        order.cancelled_at = _to_dt(o.get("cancelled_at"))
        order.closed_at = _to_dt(o.get("closed_at"))
        order.shopify_created_at = _to_dt(o.get("created_at"))
        order.processed_at = _to_dt(o.get("processed_at"))
        order.raw = o

    @staticmethod
    def _upsert_items(sess: Session, order: Order, line_items: list[dict]) -> None:
        existing = {
            it.shopify_line_item_id: it for it in sess.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            ).scalars()
        }
        for li in line_items:
            li_id = li.get("id")
            item = existing.get(li_id)
            if item is None:
                item = OrderItem(order_id=order.id, shopify_line_item_id=li_id)
                sess.add(item)
            item.shopify_product_id = li.get("product_id")
            item.shopify_variant_id = li.get("variant_id")
            item.inventory_item_id = li.get("inventory_item_id")
            item.title = li.get("title") or ""
            item.sku = li.get("sku") or ""
            item.quantity = li.get("quantity") or 0
            item.fulfillable_quantity = li.get("fulfillable_quantity") or 0
            item.price = _dec(li.get("price"))
            item.total_discount = _dec(li.get("total_discount"))
            item.grams = li.get("grams") or 0
            item.properties = li.get("properties")

    # ------------------------------------------------------------------
    def list_orders(
        self,
        store_id: int | None = None,
        local_status: str | None = None,
        financial_status: str | None = None,
        fulfillment_status: str | None = None,
        channel: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        with session_scope() as s:
            stmt = select(Order)
            count_stmt = select(func.count(Order.id))
            if store_id:
                stmt = stmt.where(Order.store_id == store_id)
                count_stmt = count_stmt.where(Order.store_id == store_id)
            if local_status:
                stmt = stmt.where(Order.local_status == local_status)
                count_stmt = count_stmt.where(Order.local_status == local_status)
            if financial_status:
                stmt = stmt.where(Order.financial_status == financial_status)
                count_stmt = count_stmt.where(Order.financial_status == financial_status)
            if fulfillment_status:
                stmt = stmt.where(Order.fulfillment_status == fulfillment_status)
                count_stmt = count_stmt.where(Order.fulfillment_status == fulfillment_status)
            if channel:
                stmt = stmt.where(Order.channel == channel)
                count_stmt = count_stmt.where(Order.channel == channel)
            if date_from:
                stmt = stmt.where(Order.shopify_created_at >= _to_dt(date_from))
                count_stmt = count_stmt.where(Order.shopify_created_at >= _to_dt(date_from))
            if date_to:
                stmt = stmt.where(Order.shopify_created_at <= _to_dt(date_to))
                count_stmt = count_stmt.where(Order.shopify_created_at <= _to_dt(date_to))

            total = s.execute(count_stmt).scalar() or 0
            rows = (
                s.execute(
                    stmt.order_by(Order.shopify_created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
                .scalars()
                .all()
            )
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [self._order_dict(r) for r in rows],
            }

    def get_order(self, order_id: int) -> dict:
        from shopify_admin.models.fulfillment import FulfillmentOrder

        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                raise NotFoundError(f"订单不存在: {order_id}")
            items = s.execute(select(OrderItem).where(OrderItem.order_id == order_id)).scalars().all()
            fos = s.execute(
                select(FulfillmentOrder).where(FulfillmentOrder.order_id == order_id)
            ).scalars().all()
            data = self._order_dict(order)
            data["items"] = [self._item_dict(it) for it in items]
            data["fulfillments"] = [
                {
                    "id": f.id, "channel": f.channel, "status": f.status,
                    "cs_order_id": f.cs_order_id, "channel_order_ref": f.channel_order_ref,
                    "tracking_number": f.tracking_number, "tracking_url": f.tracking_url,
                    "error_message": f.error_message, "exception_type": f.exception_type,
                }
                for f in fos
            ]
            return data

    # ------------------------------------------------------------------
    def close_order(self, order_id: int) -> dict:
        """订单确认（关闭）。"""
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                raise NotFoundError(f"订单不存在: {order_id}")
            client = self._stores.get_client(order.store_id)
        try:
            closed = ShopifyRest(client).close_order(order.shopify_order_id)
            with session_scope() as s:
                order = s.get(Order, order_id)
                order.closed_at = _to_dt(closed.get("closed_at"))
            return {"closed": True, "order_id": order_id}
        finally:
            client.close()

    def cancel_order(self, order_id: int, restock: bool = True) -> dict:
        with session_scope() as s:
            order = s.get(Order, order_id)
            if order is None:
                raise NotFoundError(f"订单不存在: {order_id}")
            client = self._stores.get_client(order.store_id)
        try:
            ShopifyRest(client).client.request(
                "POST", f"orders/{order.shopify_order_id}/cancel.json",
                json_body={"restock": restock},
            )
            with session_scope() as s:
                order = s.get(Order, order_id)
                order.local_status = "cancelled"
            return {"cancelled": True, "order_id": order_id}
        finally:
            client.close()

    # ------------------------------------------------------------------
    @staticmethod
    def _order_dict(o: Order) -> dict:
        return {
            "id": o.id,
            "store_id": o.store_id,
            "shopify_order_id": o.shopify_order_id,
            "name": o.name,
            "email": o.email,
            "financial_status": o.financial_status,
            "fulfillment_status": o.fulfillment_status,
            "local_status": o.local_status,
            "channel": o.channel,
            "currency": o.currency,
            "total_price": float(o.total_price) if o.total_price is not None else None,
            "shopify_created_at": o.shopify_created_at.isoformat() if o.shopify_created_at else None,
            "cancelled": o.cancelled_at is not None,
            "is_test": o.is_test,
        }

    @staticmethod
    def _item_dict(it: OrderItem) -> dict:
        return {
            "id": it.id,
            "shopify_line_item_id": it.shopify_line_item_id,
            "title": it.title,
            "sku": it.sku,
            "cs_id": it.cs_id,
            "quantity": it.quantity,
            "fulfillable_quantity": it.fulfillable_quantity,
            "price": float(it.price) if it.price is not None else None,
        }


class _session_ctx:
    """兼容传入会话/新建会话两种模式。"""

    def __init__(self, session: Session | None):
        self._session = session
        self._own = session is None

    def __enter__(self) -> Session:
        if self._own:
            self._scope = session_scope()
            return self._scope.__enter__()
        return self._session

    def __exit__(self, *args) -> None:
        if self._own:
            self._scope.__exit__(*args)
