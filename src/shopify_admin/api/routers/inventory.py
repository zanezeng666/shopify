# -*- coding: utf-8 -*-
"""库存管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[RequireApiKey])
_svc = InventoryService()


class ChannelStock(BaseModel):
    sku: str
    available: int
    cs_id: str = ""
    channel: str = ""


class ApplyBody(BaseModel):
    store_id: int
    stocks: list[ChannelStock]
    dry_run: bool = False


class PolicyBody(BaseModel):
    channel: str | None = None
    ratio: float | None = None
    min_qty: int | None = None
    max_qty: int | None = None
    priority: int | None = None
    enabled: bool | None = None
    note: str | None = None


@router.post("/locations/sync")
def sync_locations(store_id: int):
    return _svc.sync_locations(store_id)


@router.get("/levels")
def list_levels(
    store_id: int, sku: str | None = None,
    page: int = 1, page_size: int = Query(default=50, le=200),
):
    return _svc.list_levels(store_id, sku=sku, page=page, page_size=page_size)


@router.post("/sync")
def apply_stock(body: ApplyBody):
    return _svc.apply_channel_stock(
        body.store_id, [st.model_dump() for st in body.stocks], dry_run=body.dry_run
    ).model_dump()


@router.get("/sync-logs")
def sync_logs(store_id: int, limit: int = Query(default=100, le=500)):
    return {"items": _svc.list_sync_logs(store_id, limit)}


@router.get("/low-stock")
def low_stock(store_id: int, threshold: int = 5):
    return {"items": _svc.low_stock(store_id, threshold)}


@router.get("/policies")
def list_policies(store_id: int):
    return {"items": _svc.list_policies(store_id)}


@router.put("/policies/{sku_pattern}")
def upsert_policy(store_id: int, sku_pattern: str, body: PolicyBody):
    return _svc.upsert_policy(
        store_id, sku_pattern, **{k: v for k, v in body.model_dump().items() if v is not None}
    )
