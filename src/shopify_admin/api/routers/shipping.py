# -*- coding: utf-8 -*-
"""运费同步路由。

- POST /shopify/callback/carrier-rates   Shopify Carrier Service 结账实时回调
  （匿名：由 X-Shopify-Hmac-Sha256 验签保护；店铺无 api_secret 时放行——
   新式 token-only 自定义 App 场景，运费计算本身不依赖店铺凭据）
- POST /shipping/carrier/register        注册承运商到店铺（幂等：同名先删后建）
- GET  /shipping/carrier/list            店铺已有承运商列表
- DELETE /shipping/carrier/{service_id}  移除承运商
- POST /shipping/rates/quote             运费试算（CS 基数 ×1.2 对照，调试/对账用）
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.config.settings import settings
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.shipping import ShippingRateService
from shopify_admin.services.stores.service import StoreService

router = APIRouter(tags=["shipping"])
_svc = ShippingRateService()
_stores = StoreService()

CARRIER_NAME = "CS Shipping Rates"


# ----------------------------------------------------------------------
# Shopify 结账回调（承运商实时运费）
# ----------------------------------------------------------------------
@router.post("/shopify/callback/carrier-rates")
async def carrier_rates_callback(request: Request):
    """Shopify 结账时回调：按购物车总重 + 目的邮编查 CS 费率表 ×markup 返回。

    请求体 {"rate": {"items": [{sku, grams, quantity}], "destination": {...}}}；
    响应 {"rates": [{service_name, service_code, total_price(分), currency}]}。
    """
    raw = await request.body()
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    creds = _stores.find_credentials_by_domain(shop_domain)
    if creds is not None and creds.api_secret:
        expected = base64.b64encode(
            hmac.new(creds.api_secret.encode(), raw, hashlib.sha256).digest()
        ).decode()
        if not hmac.compare_digest(expected, request.headers.get("X-Shopify-Hmac-Sha256", "")):
            logger.warning(f"[shipping] 回调验签失败 shop={shop_domain}")
            raise HTTPException(401, "HMAC 校验失败")
    elif not creds:
        logger.info(f"[shipping] 回调来自未登记店铺 {shop_domain or '未知'}，按全局费率表报价")

    try:
        rate = json.loads(raw).get("rate", {})
    except json.JSONDecodeError:
        raise HTTPException(400, "请求体不是合法 JSON")

    items = rate.get("items", [])
    destination = rate.get("destination", {}) or {}
    rates = _svc.shopify_rates(items, destination)
    return {"rates": rates}


# ----------------------------------------------------------------------
# 承运商注册管理
# ----------------------------------------------------------------------
@router.post("/shipping/carrier/register", dependencies=[RequireApiKey])
def register_carrier(store_id: int, callback_base_url: str | None = None):
    """把本服务注册为店铺承运商（Shopify 后台 Settings→Shipping→Custom carrier）。

    callback_base_url 缺省取 settings.shipping_callback_base_url；
    同名承运商已存在时先删旧再建（幂等重建，避免重复条目）。
    """
    base = (callback_base_url or settings.shipping_callback_base_url).strip().rstrip("/")
    if not base:
        raise HTTPException(400, "未配置公网回调基址（settings.shipping_callback_base_url）")
    if not base.startswith("https://"):
        raise HTTPException(400, "回调地址必须 HTTPS（Shopify 要求）")

    client = _stores.get_client(store_id)
    try:
        rest = ShopifyRest(client)
        removed = []
        for cs in rest.list_carrier_services():
            if cs.get("name") == CARRIER_NAME:
                rest.delete_carrier_service(cs["id"])
                removed.append(cs["id"])
        created = rest.create_carrier_service({
            "name": CARRIER_NAME,
            "callback_url": f"{base}/shopify/callback/carrier-rates",
            "service_discovery": True,
            "active": True,
        })
    finally:
        client.close()
    logger.info(f"[shipping] carrier 注册 store={store_id} removed={removed} -> id={created.get('id')}")
    return {"store_id": store_id, "removed_ids": removed, "carrier_service": created}


@router.get("/shipping/carrier/list", dependencies=[RequireApiKey])
def list_carriers(store_id: int):
    client = _stores.get_client(store_id)
    try:
        return {"store_id": store_id, "carrier_services": ShopifyRest(client).list_carrier_services()}
    finally:
        client.close()


@router.delete("/shipping/carrier/{service_id}", dependencies=[RequireApiKey])
def delete_carrier(store_id: int, service_id: int):
    client = _stores.get_client(store_id)
    try:
        ShopifyRest(client).delete_carrier_service(service_id)
    finally:
        client.close()
    return {"store_id": store_id, "deleted": service_id}


# ----------------------------------------------------------------------
# 运费试算（对账/调试）
# ----------------------------------------------------------------------
class QuoteBody(BaseModel):
    cs_id: str | None = None       # 二选一：按产品算总重
    quantity: int = 1
    grams: int | None = None       # 二选一：直接给总重（优先）
    zip_code: str
    origin: str | None = None      # 缺省 settings.shipping_origin


@router.post("/shipping/rates/quote", dependencies=[RequireApiKey])
def quote(body: QuoteBody):
    """CS 基数与 ×markup 展示价对照（Shopify 结账页将展示 price 字段）。"""
    if body.grams:
        total = body.grams
    elif body.cs_id:
        total = _svc._unit_weight(body.cs_id) * body.quantity
    else:
        raise HTTPException(400, "cs_id 与 grams 至少提供一项")
    result = _svc.quote_weight(total, body.zip_code, origin=body.origin)
    if "error" in result:
        raise HTTPException(422, result["error"])
    return result
