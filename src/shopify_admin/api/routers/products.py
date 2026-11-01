# -*- coding: utf-8 -*-
"""产品管理路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from shopify_admin.api.deps import RequireApiKey
from shopify_admin.config.settings import settings
from shopify_admin.services.products.service import ProductService
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

router = APIRouter(prefix="/products", tags=["products"], dependencies=[RequireApiKey])
_svc = ProductService()
_cs = CsShopifySyncService()


class ProductSyncBody(BaseModel):
    store_id: int
    updated_at_min: str | None = None
    max_pages: int = 40


class PriceBody(BaseModel):
    store_id: int
    variant_id: int
    price: str


class BatchPriceBody(BaseModel):
    store_id: int
    prices: dict[str, str]  # {shopify_variant_id: price}


class SeoBody(BaseModel):
    store_id: int
    title: str | None = None
    seo_title: str | None = None
    seo_description: str | None = None
    tags: str | None = None


@router.get("")
def list_products(
    store_id: int | None = None,
    title_like: str | None = None,
    handle: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = Query(default=20, le=100),
):
    return _svc.list_products(
        store_id=store_id, title_like=title_like, handle=handle,
        status=status, page=page, page_size=page_size,
    )


@router.get("/{product_id}")
def get_product(product_id: int):
    return _svc.get_product(product_id)


@router.post("/sync")
def sync_products(body: ProductSyncBody):
    return _svc.sync_products(
        body.store_id, updated_at_min=body.updated_at_min, max_pages=body.max_pages
    ).model_dump()


@router.post("/prices")
def update_price(body: PriceBody):
    return _svc.update_variant_price(body.store_id, body.variant_id, body.price)


@router.post("/prices/batch")
def batch_update_prices(body: BatchPriceBody):
    prices = {int(k): v for k, v in body.prices.items()}
    return {"results": _svc.batch_update_prices(body.store_id, prices)}


@router.post("/{product_id}/seo")
def update_seo(product_id: int, body: SeoBody):
    return _svc.update_product_seo(
        body.store_id, product_id,
        title=body.title, seo_title=body.seo_title,
        seo_description=body.seo_description, tags=body.tags,
    )


@router.post("/collections/sync")
def sync_collections(store_id: int):
    return _svc.sync_collections(store_id)


# ------------------------------------------------------------------
# CS 产品库 → Shopify 同步（对账 + 分级执行）
# ------------------------------------------------------------------
class CsApplyBody(BaseModel):
    store_id: int
    dry_run: bool = True                  # 默认只返回计划统计，不写店铺
    price_mode: str = "report"            # report=只报告价格漂移 | overwrite=强制对齐 CS 零售价
    publish_status: str = "active"        # 新品发布形态 active | draft
    max_ops: int = Query(default=200, le=2000)  # 创建/更新各上限（限流收敛）


@router.get("/cs/diff")
def cs_sync_diff(
    store_id: int,
    price_mode: str = "report",
    sample: int = Query(default=50, le=500),
):
    """对账预览：CS 在售 ↔ 店铺锚定变体（创建/更新/停产/孤儿/价格漂移报告），纯只读。"""
    return _cs.diff(store_id, price_mode=price_mode, sample=sample)


@router.post("/cs/apply")
def cs_sync_apply(body: CsApplyBody):
    """执行对账结果：发布新品（幂等）+ 条码补空 + 重量对齐；价格按 price_mode。"""
    return _cs.apply(
        body.store_id,
        dry_run=body.dry_run,
        price_mode=body.price_mode,
        publish_status=body.publish_status,
        max_ops=body.max_ops,
    )


@router.post("/cs/refresh")
def cs_sync_refresh(rcustomerno: str | None = None):
    """触发 CS 产品镜像刷新（bmai：CIM 导出 → cs_new.cs_product）。"""
    if not rcustomerno:
        rcustomerno = settings.bmai_rcustomerno
    if not rcustomerno:
        raise HTTPException(400, "缺少 rcustomerno（店铺未配置且全局未设置）")
    return _cs.refresh_cs_catalog(rcustomerno)
