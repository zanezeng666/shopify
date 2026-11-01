# -*- coding: utf-8 -*-
"""FastAPI 依赖注入：鉴权、DB 会话、服务实例。"""
from __future__ import annotations

from typing import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from shopify_admin.core.database import get_engine
from shopify_admin.core.security import require_api_key

# 鉴权依赖（未配置 API_KEYS 时放行）
RequireApiKey = Depends(require_api_key)


def get_db() -> Iterator[Session]:
    """请求级 DB 会话（只读用途为主；写操作服务内部自管事务）。"""
    from shopify_admin.core.database import _session_factory

    get_engine()
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Depends(get_db)
