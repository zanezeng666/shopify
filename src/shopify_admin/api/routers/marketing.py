# -*- coding: utf-8 -*-
"""营销路由：Google 商品字段 + GMC Feed。"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.marketing.service import MarketingService

router = APIRouter(prefix="/marketing", tags=["marketing"], dependencies=[RequireApiKey])
_svc = MarketingService()


class GoogleFieldBody(BaseModel):
    shopify_product_id: int
    shopify_variant_id: int | None = None
    mpn: str | None = None
    brand: str | None = None
    gtin: str | None = None
    google_product_category: str | None = None
    condition: str | None = None
    custom_label0: str | None = None
    custom_label1: str | None = None
    custom_label2: str | None = None
    custom_label3: str | None = None
    custom_label4: str | None = None


class FeedBody(BaseModel):
    country: str = "US"
    currency: str = "USD"
    availability_default: str = "in_stock"


@router.get("/google-fields")
def list_google_fields(store_id: int, mpn_like: str | None = None):
    return {"items": _svc.list_google_fields(store_id, mpn_like)}


@router.put("/google-fields")
def upsert_google_field(store_id: int, body: GoogleFieldBody):
    return _svc.upsert_google_field(
        store_id, body.shopify_product_id, body.shopify_variant_id,
        **{k: v for k, v in body.model_dump().items()
           if v is not None and k not in ("shopify_product_id", "shopify_variant_id")},
    )


@router.post("/gmc-feed/generate")
def generate_feed(store_id: int, body: FeedBody):
    return _svc.generate_gmc_feed(
        store_id, country=body.country, currency=body.currency,
        availability_default=body.availability_default,
    )


@router.get("/gmc-feeds")
def list_feeds(store_id: int, limit: int = 20):
    return {"items": _svc.list_gmc_feeds(store_id, limit)}
