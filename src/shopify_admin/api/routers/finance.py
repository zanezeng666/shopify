# -*- coding: utf-8 -*-
"""财务路由：payout / 交易流水 / 成本核算 / 利润汇总。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.finance.service import FinanceService

router = APIRouter(prefix="/finance", tags=["finance"], dependencies=[RequireApiKey])
_svc = FinanceService()


class PayoutSyncBody(BaseModel):
    store_id: int
    max_pages: int = 5


class TransactionSyncBody(BaseModel):
    store_id: int
    order_id: int | None = None
    max_pages: int = 5


@router.post("/payouts/sync")
def sync_payouts(body: PayoutSyncBody):
    return _svc.sync_payouts(body.store_id, max_pages=body.max_pages)


@router.get("/payouts")
def list_payouts(
    store_id: int, status: str | None = None,
    page: int = 1, page_size: int = Query(default=20, le=100),
):
    return _svc.list_payouts(store_id, status=status, page=page, page_size=page_size)


@router.post("/transactions/sync")
def sync_transactions(body: TransactionSyncBody):
    return _svc.sync_transactions(body.store_id, order_id=body.order_id, max_pages=body.max_pages)


@router.get("/transactions")
def list_transactions(
    store_id: int, kind: str | None = None,
    page: int = 1, page_size: int = Query(default=50, le=200),
):
    return _svc.list_transactions(store_id, kind=kind, page=page, page_size=page_size)


@router.post("/order-cost/{order_id}")
def calc_order_cost(order_id: int):
    return _svc.calc_order_cost(order_id)


@router.get("/summary")
def summary(store_id: int, date_from: str | None = None, date_to: str | None = None):
    return _svc.summary(store_id, date_from, date_to)
