# -*- coding: utf-8 -*-
"""Alembic 迁移环境 — 目标库 shopify_new，元数据来自 shopify_admin.models。"""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from shopify_admin.config.settings import settings

# 导入全部模型，确保 Base.metadata 完整
from shopify_admin.models.base import Base  # noqa: E402
import shopify_admin.models  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 动态构建数据库 URL（.env 的 SHOPIFY_DB_*）。
# 不写入 config（configparser 的 % 插值与 URL 编码字符冲突）。
from urllib.parse import quote_plus


def _db_url() -> str:
    return (
        f"mysql+pymysql://{quote_plus(settings.shopify_db_user)}:{quote_plus(settings.shopify_db_password)}"
        f"@{settings.shopify_db_host}:{settings.shopify_db_port}/{settings.shopify_db_name}"
        f"?charset={settings.shopify_db_charset}"
    )


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine

    connectable = create_engine(_db_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
