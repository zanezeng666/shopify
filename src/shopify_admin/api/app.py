# -*- coding: utf-8 -*-
"""FastAPI 应用工厂：路由聚合 + 接口测试台 + 异常处理 + 健康检查。

启动：uv run uvicorn shopify_admin.api.app:app --port 8800
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from loguru import logger

from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import register_exception_handlers
from shopify_admin.core.logging import setup_logging


@asynccontextmanager
async def _lifespan(app: FastAPI):
    sched = None
    if settings.scheduler_enabled:
        from shopify_admin.scheduler import build_scheduler

        sched = build_scheduler()
        sched.start()
        logger.info("APScheduler 已启动（进程内托管）")
    yield
    if sched is not None:
        sched.shutdown(wait=False)
        logger.info("APScheduler 已停止")


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="Shopify Admin API",
        description=(
            "Shopify 店铺管理系统 REST API——订单/产品/库存/履约/财务/报表/营销。"
            "与 MCP Server 共享同一服务层。鉴权：X-API-Key 请求头。"
        ),
        version="0.1.0",
        lifespan=_lifespan,
    )
    register_exception_handlers(app)

    from shopify_admin.api.routers import (
        finance, fulfillment, inventory, marketing, orders, products, reports, shipping, stores, tasks,
    )

    for r in (stores, orders, products, inventory, fulfillment, finance, reports, marketing, shipping, tasks):
        app.include_router(r.router)

    @app.get("/health", tags=["meta"])
    def health():
        return {"ok": True, "service": "shopify-admin"}

    # 接口测试台（自包含单页，自动发现 /openapi.json 全部接口）
    _console_html = (Path(__file__).parent / "console.html").read_text(encoding="utf-8")

    @app.get("/console", include_in_schema=False)
    @app.get("/", include_in_schema=False)
    def console():
        return HTMLResponse(_console_html)

    return app


app = create_app()
