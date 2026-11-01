# -*- coding: utf-8 -*-
"""统一业务错误体系 + FastAPI 全局异常转换。

REST 响应错误结构（JSON）:
    {"error": {"code": "SHOPIFY_API_ERROR", "message": "...", "details": {...}}}

MCP 工具捕获 AppError 后转为结构化中文说明，保证 AI 可读。
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger


class AppError(Exception):
    """业务错误基类。"""

    code = "APP_ERROR"
    http_status = 400

    def __init__(self, message: str = "", details: dict[str, Any] | None = None):
        self.message = message or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "details": self.details}


class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = 404


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    http_status = 403


class ConflictError(AppError):
    code = "CONFLICT"
    http_status = 409


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422


class ShopifyAPIError(AppError):
    """Shopify Admin API 调用失败（网络/限流耗尽/响应异常）。"""

    code = "SHOPIFY_API_ERROR"
    http_status = 502


class ChannelError(AppError):
    """履约渠道（CS/FastRite）调用失败。"""

    code = "CHANNEL_ERROR"
    http_status = 502

    def __init__(self, message: str, channel: str = "", details: dict | None = None):
        merged = {"channel": channel} if channel else {}
        if details:
            merged.update(details)
        super().__init__(message, details=merged or None)


class RouteError(AppError):
    """分仓路由失败（无可用渠道/库存不足等）。"""

    code = "ROUTE_ERROR"
    http_status = 422


class MigrationError(AppError):
    code = "MIGRATION_ERROR"
    http_status = 500


def error_response(err: AppError) -> dict[str, Any]:
    """统一错误体（MCP 与 REST 共用）。"""
    return {"error": err.to_dict()}


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI 全局异常处理：AppError → 统一 JSON；未预期异常 → 500。"""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.http_status,
            content=error_response(exc),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception(f"未预期异常: {exc}")
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": str(exc), "details": {}}},
        )
