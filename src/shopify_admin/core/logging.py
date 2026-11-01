# -*- coding: utf-8 -*-
"""loguru 日志配置 + 凭据脱敏。

任何 settings 中的 password/secret/token 类值在日志输出时自动替换为 ***，
防止凭据泄漏到日志文件。
"""
from __future__ import annotations

from pathlib import Path

from loguru import logger

from shopify_admin.config.settings import settings

_configured = False


def _collect_secrets() -> list[str]:
    """收集需要脱敏的敏感配置值。"""
    secret_fields = (
        "shopify_db_password", "legacy_db_password",
        "cs_db_password", "cs_cim_password", "fastrite_db_password",
        "smtp_password", "fastrite_app_secret", "api_keys",
    )
    secrets: list[str] = []
    for f in secret_fields:
        v = getattr(settings, f, "")
        if isinstance(v, str) and len(v) >= 4:
            secrets.append(v)
    return secrets


def sanitize(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s in text:
            text = text.replace(s, "***")
    return text


def setup_logging(log_dir: str | Path = "Logs", level: str = "INFO",
                  console: bool | str = True) -> None:
    """初始化日志：控制台 + 文件（rotation 保留）。幂等。

    :param console: True=stdout；"stderr"（stdio MCP 必须用，避免污染 JSONRPC 通道）；False=关闭
    """
    global _configured
    if _configured:
        return

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    if console == "stderr":
        import sys as _sys

        logger.add(lambda m: print(m, end="", file=_sys.stderr), level=level, colorize=True)
    elif console:
        logger.add(lambda m: print(m, end=""), level=level, colorize=True)
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level=level,
        rotation="00:00",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
    )

    # 凭据脱敏 patcher
    secrets = _collect_secrets()
    if secrets:
        def _patcher(record):
            record["message"] = sanitize(record["message"], secrets)
            return True

        logger.configure(patcher=_patcher)

    _configured = True
