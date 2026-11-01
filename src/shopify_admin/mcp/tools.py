# -*- coding: utf-8 -*-
"""MCP 工具集——业务服务的薄封装（与 REST 共享同一服务层）。

命名 shopify_* 前缀；权限分级见 permission.py；
所有业务异常统一转为 {"error": "中文说明 (CODE)"} 保证 AI 可读。
"""
from __future__ import annotations

from loguru import logger

from shopify_admin.core.exceptions import AppError
from shopify_admin.mcp.permission import Permission, require
from shopify_admin.services.finance.service import FinanceService
from shopify_admin.services.fulfillment.service import FulfillmentService
from shopify_admin.services.inventory.service import InventoryService
from shopify_admin.services.marketing.service import MarketingService
from shopify_admin.services.orders.service import OrderService
from shopify_admin.services.products.service import ProductService
from shopify_admin.services.reports.service import ReportService
from shopify_admin.services.stores.service import StoreService

# 模块级服务实例（无状态，可复用）
_stores = StoreService()
_orders = OrderService()
_products = ProductService()
_inventory = InventoryService()
_fulfillment = FulfillmentService()
_finance = FinanceService()
_reports = ReportService()
_marketing = MarketingService()


def _guard(fn, *args, **kwargs):
    """统一异常转换：AppError -> {"error": "...(CODE)"}；未知异常保留堆栈日志。"""
    try:
        return fn(*args, **kwargs)
    except AppError as e:
        return {"error": f"{e.message} ({e.code})"}
    except Exception as e:  # noqa: BLE001
        logger.exception(f"[mcp] 工具执行失败: {e}")
        return {"error": f"内部错误: {e}"}


# ======================================================================
# 店铺
# ======================================================================
def shopify_stores_list(available_only: bool = False) -> list[dict]:
    """列出全部店铺（id/名称/域名/可用性）。

    :param available_only: 仅返回凭据可用的店铺
    """
    return _stores.list_stores(available_only=available_only)


def shopify_store_get(store_id: int) -> dict:
    """查单个店铺详情。"""
    return _guard(_stores.get_store, store_id)


def shopify_store_verify(store_id: int) -> dict:
    """检测店铺 Shopify 凭据连通性（不计费，只发 shop.get 请求）。"""
    return _guard(lambda: _stores.verify(store_id)._asdict())


# ======================================================================
# 订单
# ======================================================================
def shopify_orders_list(
    store_id: int | None = None,
    local_status: str | None = None,
    financial_status: str | None = None,
    fulfillment_status: str | None = None,
    channel: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """查询本地订单库（多条件筛选，分页）。

    :param store_id: 店铺 ID（空=全部店铺）
    :param local_status: 本地状态 pending/routed/submitted/shipped/failed/cancelled/completed
    :param financial_status: Shopify 资金状态 paid/pending/refunded...
    :param channel: 履约渠道 cs/fastrite/manual
    :param date_from/date_to: 日期范围 YYYY-MM-DD
    """
    return _guard(
        _orders.list_orders, store_id=store_id, local_status=local_status,
        financial_status=financial_status, fulfillment_status=fulfillment_status,
        channel=channel, date_from=date_from, date_to=date_to,
        page=page, page_size=page_size,
    )


def shopify_order_get(order_id: int) -> dict:
    """查单个订单详情（含行项与履约信息）。"""
    return _guard(_orders.get_order, order_id)


@require(Permission.GENERAL)
def shopify_orders_sync(store_id: int, created_at_min: str | None = None, max_pages: int = 5) -> dict:
    """从 Shopify 增量拉取订单到本地库。

    :param created_at_min: 起始时间 ISO 格式（空=自动按库里最新订单续拉）
    :param max_pages: 最多拉取页数（每页 250）
    """
    return _guard(_orders.sync_orders, store_id, created_at_min=created_at_min, max_pages=max_pages)


@require(Permission.ADMIN)
def shopify_order_close(order_id: int) -> dict:
    """关闭本地订单（close，不退库存）。"""
    return _guard(_orders.close_order, order_id)


@require(Permission.ADMIN)
def shopify_order_cancel(order_id: int, restock: bool = True) -> dict:
    """取消订单（本地 + Shopify，可选恢复库存）。"""
    return _guard(_orders.cancel_order, order_id, restock=restock)


# ======================================================================
# 产品
# ======================================================================
def shopify_products_list(
    store_id: int | None = None, title_like: str | None = None,
    sku: str | None = None, status: str | None = None,
    page: int = 1, page_size: int = 20,
) -> dict:
    """查询产品与变体（分页）。"""
    return _guard(
        _products.list_products, store_id=store_id, title_like=title_like,
        sku=sku, status=status, page=page, page_size=page_size,
    )


def shopify_product_get(product_id: int) -> dict:
    """查单个产品详情（含全部变体/价格/SEO/条码）。"""
    return _guard(_products.get_product, product_id)


@require(Permission.GENERAL)
def shopify_products_sync(store_id: int, max_pages: int = 10) -> dict:
    """从 Shopify 同步产品与变体到本地库。"""
    return _guard(_products.sync_products, store_id, max_pages=max_pages)


@require(Permission.GENERAL)
def shopify_collections_sync(store_id: int) -> dict:
    """同步店铺 Collections 到本地库。"""
    return _guard(_products.sync_collections, store_id)


@require(Permission.ADMIN)
def shopify_price_update(store_id: int, variant_id: int, price: str | float) -> dict:
    """更新单个变体价格（本地 + Shopify 双写）。"""
    return _guard(_products.update_variant_price, store_id, variant_id, price)


@require(Permission.ADMIN)
def shopify_prices_batch(store_id: int, prices: dict[str, str | float]) -> dict:
    """批量改价。prices: {variant_id: 新价格}（键为字符串形式的变体 ID）。"""
    parsed = {int(k): v for k, v in prices.items()}
    return _guard(_products.batch_update_prices, store_id, parsed)


@require(Permission.ADMIN)
def shopify_product_seo_update(
    store_id: int, product_id: int,
    title: str | None = None, seo_title: str | None = None,
    seo_description: str | None = None,
) -> dict:
    """更新产品标题/SEO 字段（本地 + Shopify 双写）。"""
    return _guard(
        _products.update_product_seo, store_id, product_id,
        title=title, seo_title=seo_title, seo_description=seo_description,
    )


# ======================================================================
# 库存
# ======================================================================
def shopify_inventory_levels(store_id: int, sku: str | None = None, page: int = 1, page_size: int = 50) -> dict:
    """查 Shopify 库存水位（本地镜像）。"""
    return _guard(_inventory.list_levels, store_id, sku=sku, page=page, page_size=page_size)


def shopify_inventory_low_stock(store_id: int, threshold: int = 5) -> list[dict]:
    """低库存预警列表。"""
    return _guard(_inventory.low_stock, store_id, threshold=threshold)


def shopify_inventory_logs(store_id: int, limit: int = 50) -> list[dict]:
    """库存同步日志。"""
    return _guard(_inventory.list_sync_logs, store_id, limit=limit)


def shopify_inventory_policies(store_id: int) -> list[dict]:
    """库存同步策略列表。"""
    return _guard(_inventory.list_policies, store_id)


@require(Permission.GENERAL)
def shopify_inventory_channel(sku: str) -> dict:
    """查 SKU 在两个履约渠道（CS/FastRite）的实时可用库存。"""
    from shopify_admin.channels.registry import available_channels, get_channel

    out: dict = {"sku": sku, "channels": {}}
    for name in available_channels():
        try:
            inv = get_channel(name).get_inventory(sku)
            out["channels"][name] = {"available": inv.available, "raw": inv.raw}
        except Exception as e:  # noqa: BLE001
            out["channels"][name] = {"error": str(e)[:200]}
    return out


@require(Permission.GENERAL)
def shopify_inventory_apply(store_id: int, skus: list[str], dry_run: bool = False) -> dict:
    """把渠道库存同步到 Shopify（查渠道→策略计算→写 Shopify）。

    :param skus: 要同步的 SKU 列表
    :param dry_run: 只计算不落库
    """
    from shopify_admin.channels.registry import get_channel
    from shopify_admin.models.product import ProductVariant
    from shopify_admin.core.database import session_scope
    from sqlalchemy import select

    # SKU -> cs_id 解析（变体缓存）
    with session_scope() as s:
        rows = s.execute(
            select(ProductVariant.sku, ProductVariant.cs_id).where(ProductVariant.sku.in_(skus))
        ).all()
    cs_ids = {sku: cs_id for sku, cs_id in rows if cs_id}

    # 渠道库存查询（FastRite 直接可用；CS 的 SKU 即 CSID 语义由渠道层解析）
    stocks: list[dict] = []
    fr = get_channel("fastrite")
    for sku in skus:
        try:
            inv = fr.get_inventory(sku)
            stocks.append({"sku": sku, "available": inv.available, "cs_id": cs_ids.get(sku, "")})
        except Exception as e:  # noqa: BLE001
            return {"error": f"渠道库存查询失败 {sku}: {str(e)[:200]}"}

    result = _inventory.apply_channel_stock(store_id, stocks, dry_run=dry_run)
    return {
        "applied": result.applied, "skipped": result.skipped, "failed": result.failed,
        "messages": result.messages[:20],
    }


@require(Permission.ADMIN)
def shopify_inventory_policy_upsert(
    store_id: int, sku_pattern: str,
    min_qty: int = 0, max_qty: int | None = None,
    safety_qty: int = 0, buffer_ratio: float = 1.0, enabled: bool = True,
) -> dict:
    """创建/更新库存同步策略（SKU 通配模式）。"""
    return _guard(
        _inventory.upsert_policy, store_id, sku_pattern,
        min_qty=min_qty, max_qty=max_qty, safety_qty=safety_qty,
        buffer_ratio=buffer_ratio, enabled=enabled,
    )


# ======================================================================
# 履约
# ======================================================================
def shopify_fulfillment_list(
    store_id: int | None = None, order_id: int | None = None,
    status: str | None = None, channel: str | None = None,
    page: int = 1, page_size: int = 20,
) -> dict:
    """履约单查询。"""
    return _guard(
        _fulfillment.list_fulfillments, store_id=store_id, order_id=order_id,
        status=status, channel=channel, page=page, page_size=page_size,
    )


@require(Permission.GENERAL)
def shopify_fulfillment_route(order_id: int, force_channel: str | None = None, dry_run: bool = False) -> dict:
    """订单分仓路由（FastRite 优先、CS 兜底、无库存转 manual）。

    :param force_channel: 强制指定渠道 cs/fastrite/manual
    :param dry_run: 只计算不落库（路由预演）
    """
    return _guard(_fulfillment.route_order, order_id, force_channel=force_channel, dry_run=dry_run)


@require(Permission.ADMIN)
def shopify_fulfillment_submit(order_id: int, channel: str | None = None) -> dict:
    """执行渠道下单（CS 代发/FastRite 出库单）。"""
    return _guard(_fulfillment.submit_order, order_id, channel=channel)


@require(Permission.GENERAL)
def shopify_fulfillment_poll(store_id: int | None = None, max_items: int = 100) -> dict:
    """轮询渠道订单状态（跟踪号自动捕获）。"""
    return _guard(_fulfillment.poll_channel_status, store_id=store_id, max_items=max_items)


@require(Permission.GENERAL)
def shopify_tracking_push(fulfillment_order_id: int, tracking_number: str,
                          tracking_company: str = "", tracking_url: str = "") -> dict:
    """跟踪号回传 Shopify（创建 fulfillment）。"""
    return _guard(
        _fulfillment.push_tracking, fulfillment_order_id,
        tracking_number, tracking_company=tracking_company, tracking_url=tracking_url,
    )


@require(Permission.ADMIN)
def shopify_fulfillment_mark_exception(fulfillment_order_id: int, exception_type: str, note: str = "") -> dict:
    """标记履约异常（insufficient_stock/discontinued/unshippable/other）。"""
    return _guard(_fulfillment.mark_exception, fulfillment_order_id, exception_type, note=note)


def shopify_shipping_quotes(sku: str, quantity: int, country_code: str, zip: str,
                            city: str = "", province: str = "", weight_g: int = 0) -> list[dict]:
    """FastRite 渠道运费试算（海外仓发货报价）。"""
    from shopify_admin.channels.base import Address, Parcel
    from shopify_admin.channels.registry import get_channel

    parcel = Parcel(weight_g=weight_g, items=[{"sku": sku, "qty": quantity}])
    dest = Address(country_code=country_code, zip=zip, city=city, province=province)
    quotes = _guard(get_channel("fastrite").calculate_shipping, parcel, dest)
    if isinstance(quotes, dict):  # 错误结构
        return [quotes]
    return [
        {"service": q.service_name, "price": str(q.price), "currency": q.currency, "eta_days": q.eta_days}
        for q in quotes
    ]


# ======================================================================
# 财务
# ======================================================================
def shopify_finance_summary(store_id: int, date_from: str | None = None, date_to: str | None = None) -> dict:
    """财务汇总（销售额/订单数/payout 概览）。"""
    return _guard(_finance.summary, store_id, date_from=date_from, date_to=date_to)


def shopify_payouts_list(store_id: int, status: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    """Shopify payout 列表。"""
    return _guard(_finance.list_payouts, store_id, status=status, page=page, page_size=page_size)


def shopify_transactions_list(store_id: int, kind: str | None = None, page: int = 1, page_size: int = 50) -> dict:
    """订单交易流水列表。"""
    return _guard(_finance.list_transactions, store_id, kind=kind, page=page, page_size=page_size)


def shopify_order_cost(order_id: int) -> dict:
    """订单成本核算（产品成本 + 最优物流 + 渠道费用 → 毛利）。"""
    return _guard(_finance.calc_order_cost, order_id)


@require(Permission.GENERAL)
def shopify_payouts_sync(store_id: int, max_pages: int = 5) -> dict:
    """同步 Shopify payout 数据。"""
    return _guard(_finance.sync_payouts, store_id, max_pages=max_pages)


@require(Permission.GENERAL)
def shopify_transactions_sync(store_id: int, order_id: int | None = None, max_pages: int = 5) -> dict:
    """同步订单交易流水。"""
    return _guard(_finance.sync_transactions, store_id, order_id=order_id, max_pages=max_pages)


# ======================================================================
# 报表
# ======================================================================
def shopify_report_sales(store_id: int, date_from: str | None = None, date_to: str | None = None,
                         by: str = "sku") -> list[dict]:
    """销量报表（按 sku/product/day 聚合）。"""
    return _guard(_reports.sales_report, store_id, date_from=date_from, date_to=date_to, by=by)


def shopify_report_order_status(store_id: int) -> dict:
    """订单状态分布报表。"""
    return _guard(_reports.order_status_report, store_id)


def shopify_report_inventory(store_id: int, low_threshold: int = 5) -> dict:
    """库存报表（含低库存预警）。"""
    return _guard(_reports.inventory_report, store_id, low_threshold=low_threshold)


# ======================================================================
# 营销（GMC）
# ======================================================================
def shopify_gmc_feeds(store_id: int, limit: int = 10) -> list[dict]:
    """GMC feed 生成历史。"""
    return _guard(_marketing.list_gmc_feeds, store_id, limit=limit)


def shopify_google_fields_list(store_id: int, mpn_like: str | None = None) -> list[dict]:
    """Google 商品字段列表。"""
    return _guard(_marketing.list_google_fields, store_id, mpn_like=mpn_like)


@require(Permission.GENERAL)
def shopify_gmc_generate(store_id: int, country: str = "US", currency: str = "USD",
                         availability_default: str = "in_stock") -> dict:
    """生成 GMC TSV feed（产品+变体+Google字段合并）。"""
    return _guard(
        _marketing.generate_gmc_feed, store_id,
        country=country, currency=currency, availability_default=availability_default,
    )


@require(Permission.ADMIN)
def shopify_google_field_upsert(
    store_id: int, shopify_product_id: int, shopify_variant_id: int | None = None,
    mpn: str | None = None, brand: str | None = None, gtin: str | None = None,
    google_product_category: str | None = None, condition: str | None = None,
    custom_label0: str | None = None, custom_label1: str | None = None,
    custom_label2: str | None = None, custom_label3: str | None = None,
    custom_label4: str | None = None,
) -> dict:
    """更新 Google 商品覆盖字段（None=不修改，空串=清空）。"""
    kwargs = {
        k: v for k, v in dict(
            mpn=mpn, brand=brand, gtin=gtin, google_product_category=google_product_category,
            condition=condition, custom_label0=custom_label0, custom_label1=custom_label1,
            custom_label2=custom_label2, custom_label3=custom_label3, custom_label4=custom_label4,
        ).items() if v is not None
    }
    return _guard(
        _marketing.upsert_google_field, store_id, shopify_product_id, shopify_variant_id, **kwargs
    )


# ======================================================================
# 工具注册表（mcp_server 聚合用）
# ======================================================================
ALL_TOOLS = [
    shopify_stores_list, shopify_store_get, shopify_store_verify,
    shopify_orders_list, shopify_order_get, shopify_orders_sync,
    shopify_order_close, shopify_order_cancel,
    shopify_products_list, shopify_product_get, shopify_products_sync,
    shopify_collections_sync, shopify_price_update, shopify_prices_batch,
    shopify_product_seo_update,
    shopify_inventory_levels, shopify_inventory_low_stock, shopify_inventory_logs,
    shopify_inventory_policies, shopify_inventory_channel, shopify_inventory_apply,
    shopify_inventory_policy_upsert,
    shopify_fulfillment_list, shopify_fulfillment_route, shopify_fulfillment_submit,
    shopify_fulfillment_poll, shopify_tracking_push, shopify_fulfillment_mark_exception,
    shopify_shipping_quotes,
    shopify_finance_summary, shopify_payouts_list, shopify_transactions_list,
    shopify_order_cost, shopify_payouts_sync, shopify_transactions_sync,
    shopify_report_sales, shopify_report_order_status, shopify_report_inventory,
    shopify_gmc_feeds, shopify_google_fields_list, shopify_gmc_generate,
    shopify_google_field_upsert,
]
