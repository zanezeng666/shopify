# -*- coding: utf-8 -*-
"""报表路由。"""
from __future__ import annotations

from fastapi import APIRouter

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[RequireApiKey])
_svc = ReportService()


@router.get("/sales")
def sales_report(
    store_id: int,
    date_from: str | None = None,
    date_to: str | None = None,
    by: str = "sku",  # sku | day
):
    return {"items": _svc.sales_report(store_id, date_from, date_to, by=by)}


@router.get("/order-status")
def order_status_report(store_id: int):
    return _svc.order_status_report(store_id)


@router.get("/inventory")
def inventory_report(store_id: int, low_threshold: int = 5):
    return _svc.inventory_report(store_id, low_threshold)
