# -*- coding: utf-8 -*-
"""Google Ads 路由：连通验证 / 账户信息 / 广告系列报表 / 转化回传。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.services.marketing.google_ads import (
    GoogleAdsConfigError,
    GoogleAdsService,
)

router = APIRouter(prefix="/google-ads", tags=["google-ads"], dependencies=[RequireApiKey])
_svc = GoogleAdsService()


class ConversionUploadBody(BaseModel):
    store_id: int | None = None
    limit: int = 200


def _bad_config(e: GoogleAdsConfigError):
    return HTTPException(status_code=400, detail=str(e))


@router.get("/verify")
def verify():
    """凭据连通验证（列出可访问的广告账户）。"""
    return _svc.verify_connection()


@router.get("/customer-info")
def customer_info(customer_id: str | None = None):
    """广告账户基础信息（名称/货币/时区）。"""
    try:
        return _svc.get_customer_info(customer_id)
    except GoogleAdsConfigError as e:
        raise _bad_config(e)


@router.get("/campaigns")
def campaigns(customer_id: str | None = None):
    """广告系列列表（预算 + 全时段核心指标）。"""
    try:
        return {"items": _svc.list_campaigns(customer_id)}
    except GoogleAdsConfigError as e:
        raise _bad_config(e)


@router.get("/conversions/pending")
def conversions_pending(store_id: int | None = None, limit: int = 200):
    """待回传转化订单（已支付 + 有 gclid + 未回传）。"""
    return _svc.pending_conversions(store_id, limit)


@router.post("/conversions/upload")
def conversions_upload(body: ConversionUploadBody):
    """触发转化回传（gclid -> Google Ads，成功标记幂等）。"""
    try:
        return _svc.upload_pending_conversions(body.store_id, body.limit)
    except GoogleAdsConfigError as e:
        raise _bad_config(e)
