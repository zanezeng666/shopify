# -*- coding: utf-8 -*-
"""MCP 权限管理——READ / GENERAL / ADMIN 三级（对齐 bmai 模式）。

定级方式：
- stdio（本地 AI 客户端）：环境变量 MCP_LEVEL=read|general|admin，缺省 read
- SSE（远程）：MCP_TOKENS="token1:admin,token2:read"，
  请求头 X-MCP-Token 匹配定级；未配置或未匹配时只读
"""
from __future__ import annotations

import functools
from contextvars import ContextVar
from enum import IntEnum

from loguru import logger

from shopify_admin.config.settings import settings


class Permission(IntEnum):
    READ = 0     # 只读查询
    GENERAL = 1  # 同步类（拉单/库存同步/状态轮询/回传）
    ADMIN = 2    # 写操作（改价/SEO/下单/订单流转）


# stdio 全局级别（启动时设定）；SSE 每请求级别（middleware 设定）
_global: Permission = Permission.READ
_request_level: ContextVar[Permission | None] = ContextVar("mcp_request_level", default=None)

_LEVEL_NAMES = {"read": Permission.READ, "general": Permission.GENERAL, "admin": Permission.ADMIN}


def init_from_env() -> Permission:
    """stdio 模式：按 MCP_LEVEL 定级。"""
    global _global
    raw = (settings.mcp_level or "read").strip().lower()
    _global = _LEVEL_NAMES.get(raw, Permission.READ)
    if raw not in _LEVEL_NAMES:
        logger.warning(f"MCP: MCP_LEVEL={raw} 非法，回退只读")
    logger.info(f"MCP: stdio 权限级别 {_global.name}")
    return _global


def resolve_token(token: str) -> Permission | None:
    """SSE 模式：按 X-MCP-Token 匹配 SHOPIFY_MCP_TOKENS 定级。未匹配返回 None（只读）。"""
    mapping = settings.mcp_tokens or ""
    for pair in mapping.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        tok, lvl = pair.rsplit(":", 1)
        if tok == token:
            return _LEVEL_NAMES.get(lvl.strip().lower(), Permission.READ)
    return None


def set_request_level(level: Permission | None) -> None:
    """SSE middleware 调用：为当前请求定级。"""
    _request_level.set(level)


def current() -> Permission:
    return _request_level.get() or _global


def require(tier: Permission):
    """工具装饰器：权限不足时返回结构化错误（AI 可读）。"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if current() < tier:
                return {
                    "error": f"权限不足（需要 {tier.name}，当前 {current().name}）。"
                    "stdio 模式设置 MCP_LEVEL；SSE 模式携带 X-MCP-Token。"
                }
            return func(*args, **kwargs)

        return wrapper

    return decorator
