# -*- coding: utf-8 -*-
"""店铺管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.stores.service import StoreService

router = APIRouter(prefix="/stores", tags=["stores"], dependencies=[RequireApiKey])
_svc = StoreService()


class StoreCreate(BaseModel):
    username: str
    api_key: str
    api_secret: str = ""
    domain: str = ""
    is_available: bool = True
    is_inventory_available: bool = False
    main_ship_by: str = "auto"


class StoreUpdate(BaseModel):
    api_key: str | None = None
    api_secret: str | None = None
    domain: str | None = None
    primary_domain: str | None = None
    is_available: bool | None = None
    is_inventory_available: bool | None = None
    main_ship_by: str | None = None
    ship_of_country_first: str | None = None


@router.get("")
def list_stores(available_only: bool = False):
    return {"items": _svc.list_stores(available_only)}


@router.get("/{store_id}")
def get_store(store_id: int):
    return _svc.get_store(store_id)


@router.post("", status_code=201)
def create_store(body: StoreCreate):
    return _svc.create_store(**body.model_dump())


@router.patch("/{store_id}")
def update_store(store_id: int, body: StoreUpdate):
    return _svc.update_store(store_id, {k: v for k, v in body.model_dump().items() if v is not None})


@router.post("/{store_id}/verify")
def verify_store(store_id: int):
    return _svc.verify(store_id).model_dump()
