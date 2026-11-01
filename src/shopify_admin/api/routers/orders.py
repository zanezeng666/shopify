# -*- coding: utf-8 -*-
"""订单管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[RequireApiKey])
_svc = OrderService()


class OrderSyncBody(BaseModel):
    store_id: int
    created_at_min: str | None = None
    financial_status: str | None = None
    max_pages: int = 20


@router.get("")
def list_orders(
    store_id: int | None = None,
    local_status: str | None = None,
    financial_status: str | None = None,
    fulfillment_status: str | None = None,
    channel: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, le=100),
):
    return _svc.list_orders(
        store_id=store_id, local_status=local_status, financial_status=financial_status,
        fulfillment_status=fulfillment_status, channel=channel,
        date_from=date_from, date_to=date_to, page=page, page_size=page_size,
    )


@router.get("/{order_id}")
def get_order(order_id: int):
    return _svc.get_order(order_id)


@router.post("/sync")
def sync_orders(body: OrderSyncBody):
    return _svc.sync_orders(
        body.store_id, created_at_min=body.created_at_min,
        financial_status=body.financial_status, max_pages=body.max_pages,
    ).model_dump()


@router.post("/{order_id}/close")
def close_order(order_id: int):
    return _svc.close_order(order_id)


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, restock: bool = True):
    return _svc.cancel_order(order_id, restock)
