# -*- coding: utf-8 -*-
"""数据库引擎管理：shopify_new 主库（可写）+ 老库（只读，仅迁移用）。

懒初始化：首次访问才建立连接，便于测试与 CLI 场景在无 DB 配置下 import。
风格对齐 bmai EngineFactory（pool_pre_ping + pool_recycle）。
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional
from urllib.parse import quote_plus

from loguru import logger
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from shopify_admin.config.settings import settings

_shopify_engine: Optional[Engine] = None
_legacy_engine: Optional[Engine] = None
_cs_engine: Optional[Engine] = None
_fastrite_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def _mysql_url(host: str, port: int, user: str, password: str, database: str, charset: str) -> str:
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{database}"
        f"?charset={charset}"
    )


def get_engine() -> Engine:
    """shopify_new 主库引擎（可写）。"""
    global _shopify_engine, _session_factory
    if _shopify_engine is None:
        if not settings.shopify_db_host:
            raise RuntimeError("未配置 SHOPIFY_DB_* 数据库连接（检查 .env）")
        url = _mysql_url(
            host=settings.shopify_db_host,
            port=settings.shopify_db_port,
            user=settings.shopify_db_user,
            password=settings.shopify_db_password,
            database=settings.shopify_db_name,
            charset=settings.shopify_db_charset,
        )
        _shopify_engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=5, max_overflow=10)
        _session_factory = sessionmaker(bind=_shopify_engine, expire_on_commit=False)
        logger.info(f"主库引擎就绪: {settings.shopify_db_host}:{settings.shopify_db_port}/{settings.shopify_db_name}")
    return _shopify_engine


def get_legacy_engine() -> Engine:
    """老库只读引擎（仅迁移脚本使用）。"""
    global _legacy_engine
    if _legacy_engine is None:
        if not settings.legacy_db_host:
            raise RuntimeError("未配置 LEGACY_DB_* 数据库连接（检查 .env）")
        url = _mysql_url(
            host=settings.legacy_db_host,
            port=settings.legacy_db_port,
            user=settings.legacy_db_user,
            password=settings.legacy_db_password,
            database=settings.legacy_db_name,
            charset="utf8mb4",
        )
        _legacy_engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=2, max_overflow=5)
        logger.info(f"老库只读引擎就绪: {settings.legacy_db_host}:{settings.legacy_db_port}/{settings.legacy_db_name}")
    return _legacy_engine


def get_cs_engine() -> Engine:
    """cs_new 库（bmai 自管）只读引擎：定时任务批量读渠道库存镜像。

    该库写路径归 bmai，本工程只 SELECT。
    """
    global _cs_engine
    if _cs_engine is None:
        if not settings.cs_db_host:
            raise RuntimeError("未配置 CS_DB_* 数据库连接（检查 .env）")
        url = _mysql_url(
            host=settings.cs_db_host,
            port=settings.cs_db_port,
            user=settings.cs_db_user,
            password=settings.cs_db_password,
            database=settings.cs_db_name,
            charset=settings.cs_db_charset or "utf8",
        )
        _cs_engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=2, max_overflow=5)
        logger.info(f"cs_new 镜像引擎就绪: {settings.cs_db_host}:{settings.cs_db_port}/{settings.cs_db_name}")
    return _cs_engine


def get_fastrite_engine() -> Engine:
    """fast_rite 库只读引擎：FastRite 库存/出库单镜像（stock_table/outbound_order）。"""
    global _fastrite_engine
    if _fastrite_engine is None:
        if not settings.fastrite_db_host:
            raise RuntimeError("未配置 FASTRITE_DB_* 数据库连接（检查 .env）")
        url = _mysql_url(
            host=settings.fastrite_db_host,
            port=settings.fastrite_db_port,
            user=settings.fastrite_db_user,
            password=settings.fastrite_db_password,
            database=settings.fastrite_db_name,
            charset="utf8",
        )
        _fastrite_engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=2, max_overflow=5)
        logger.info(f"fast_rite 镜像引擎就绪: {settings.fastrite_db_host}:{settings.fastrite_db_port}/{settings.fastrite_db_name}")
    return _fastrite_engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """事务会话上下文：正常提交、异常回滚、最终关闭。"""
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


def check_connection() -> bool:
    """主库连通性检测。"""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"主库连接失败: {e}")
        return False
