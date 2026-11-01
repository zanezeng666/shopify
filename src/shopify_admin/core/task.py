# -*- coding: utf-8 -*-
"""任务审计装饰器：执行记录写 shopify_new.task_result + 失败 SMTP 告警。

对齐老系统行为（bm.task_result）：定时任务与手动任务全量留痕，
失败时发邮件（SMTP 未配置则仅日志）。
"""
from __future__ import annotations

import functools
import smtplib
import ssl
import time
from datetime import datetime
from typing import Any, Callable

from loguru import logger

from shopify_admin.config.settings import settings


def _send_failure_email(task_name: str, error: str, duration_s: float) -> None:
    """任务失败告警邮件。SMTP 未配置时静默跳过。"""
    if not (settings.smtp_host and settings.smtp_user and settings.notify_email):
        return
    try:
        msg = (
            f"Subject: [ShopifyAdmin] 任务失败告警: {task_name}\r\n"
            f"From: {settings.smtp_user}\r\n"
            f"To: {settings.notify_email}\r\n"
            f"\r\n"
            f"任务: {task_name}\r\n耗时: {duration_s:.1f}s\r\n错误: {error}\r\n"
        )
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ctx, timeout=15) as s:
            s.login(settings.smtp_user, settings.smtp_password)
            s.sendmail(settings.smtp_user, [settings.notify_email], msg.encode("utf-8"))
        logger.info(f"失败告警邮件已发送: {task_name} -> {settings.notify_email}")
    except Exception as e:
        logger.warning(f"失败告警邮件发送异常: {e}")


def _record(task_name: str, result: str, error: str, started: datetime, duration_s: float) -> None:
    """写 task_result 表。表不存在/库不可用时仅记日志，不阻断任务本身。"""
    try:
        from shopify_admin.core.database import get_engine
        from sqlalchemy import text

        sql = (
            "INSERT INTO task_result (task_name, result, error, started_at, finished_at, duration_s) "
            "VALUES (:task_name, :result, :error, :started_at, :finished_at, :duration_s)"
        )
        with get_engine().begin() as conn:
            conn.execute(
                text(sql),
                {
                    "task_name": task_name,
                    "result": result[:2000],
                    "error": error[:2000] if error else None,
                    "started_at": started,
                    "finished_at": datetime.now(),
                    "duration_s": round(duration_s, 2),
                },
            )
    except Exception as e:
        logger.warning(f"task_result 记录失败（不影响任务结果）: {e}")


def task_record(func: Callable) -> Callable:
    """装饰器：记录任务执行结果，失败时告警并原样抛出异常。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        task_name = f"{func.__module__}.{func.__name__}"
        started = datetime.now()
        t0 = time.monotonic()
        try:
            result = func(*args, **kwargs)
            duration = time.monotonic() - t0
            summary = str(result) if result is not None else "OK"
            _record(task_name, summary, "", started, duration)
            logger.info(f"[task] {task_name} 完成 ({duration:.1f}s): {summary[:200]}")
            return result
        except Exception as e:
            duration = time.monotonic() - t0
            _record(task_name, "", f"{type(e).__name__}: {e}", started, duration)
            logger.error(f"[task] {task_name} 失败 ({duration:.1f}s): {e}")
            _send_failure_email(task_name, f"{type(e).__name__}: {e}", duration)
            raise

    return wrapper
