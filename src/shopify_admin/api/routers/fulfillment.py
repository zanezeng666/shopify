# -*- coding: utf-8 -*-
"""履约编排路由：分仓 / 下单 / 轮询 / 回传 / 异常。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.fulfillment.service import FulfillmentService

router = APIRouter(prefix="/fulfillment", tags=["fulfillment"], dependencies=[RequireApiKey])
_svc = FulfillmentService()


class RouteBody(BaseModel):
    force_channel: str | None = None  # cs | fastrite | manual
    dry_run: bool = False


class PushTrackingBody(BaseModel):
    tracking_number: str
    tracking_company: str = ""
    tracking_url: str = ""


class ExceptionBody(BaseModel):
    exception_type: str  # insufficient_balance | product_discontinued | logistics_unreachable | other
    note: str = ""


@router.post("/{order_id}/route")
def route_order(order_id: int, body: RouteBody):
    return _svc.route_order(order_id, force_channel=body.force_channel, dry_run=body.dry_run)


@router.post("/{order_id}/submit")
def submit_order(order_id: int, channel: str | None = None):
    return _svc.submit_order(order_id, channel=channel)


@router.post("/poll")
def poll_status(store_id: int | None = None, max_items: int = Query(default=100, le=500)):
    return _svc.poll_channel_status(store_id=store_id, max_items=max_items)


@router.post("/{fulfillment_id}/push-tracking")
def push_tracking(fulfillment_id: int, body: PushTrackingBody):
    return _svc.push_tracking(
        fulfillment_id, body.tracking_number,
        body.tracking_company, body.tracking_url,
    )


@router.post("/{fulfillment_id}/exception")
def mark_exception(fulfillment_id: int, body: ExceptionBody):
    return _svc.mark_exception(fulfillment_id, body.exception_type, body.note)


@router.get("/orders")
def list_fulfillments(
    store_id: int | None = None,
    order_id: int | None = None,
    status: str | None = None,
    channel: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, le=100),
):
    return _svc.list_fulfillments(
        store_id=store_id, order_id=order_id, status=status,
        channel=channel, page=page, page_size=page_size,
    )
