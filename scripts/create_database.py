# -*- coding: utf-8 -*-
"""建库脚本：CREATE DATABASE IF NOT EXISTS shopify_new。

用法:
    uv run python scripts/create_database.py

随后执行 Alembic 迁移建表:
    uv run alembic upgrade head
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pymysql  # noqa: E402

from shopify_admin.config.settings import settings  # noqa: E402


def main() -> None:
    if not settings.shopify_db_host:
        print("错误: 未配置 SHOPIFY_DB_*（先复制 .env.example 为 .env 并填写）")
        sys.exit(1)

    conn = pymysql.connect(
        host=settings.shopify_db_host,
        port=settings.shopify_db_port,
        user=settings.shopify_db_user,
        password=settings.shopify_db_password,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.shopify_db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
        print(f"数据库 `{settings.shopify_db_name}` 就绪")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
