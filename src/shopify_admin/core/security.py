# -*- coding: utf-8 -*-
"""REST API 鉴权：X-API-Key 请求头校验。

- API_KEYS 配置多个 key（逗号分隔），任一匹配即通过
- 未配置 API_KEYS = 不鉴权（仅限本地调试，启动时告警一次）
"""
from __future__ import annotations

from fastapi import Header

from loguru import logger

from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import PermissionDeniedError

_warned_no_auth = False


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """FastAPI 依赖：校验 X-API-Key。"""
    global _warned_no_auth
    keys = settings.api_key_list
    if not keys:
        if not _warned_no_auth:
            logger.warning("API_KEYS 未配置，REST API 处于无鉴权模式（仅限本地调试）")
            _warned_no_auth = True
        return
    if x_api_key is None or x_api_key not in keys:
        raise PermissionDeniedError("无效或缺失的 API Key（X-API-Key 请求头）")
