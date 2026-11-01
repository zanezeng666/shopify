# -*- coding: utf-8 -*-
"""任务审计表（core/task.py 装饰器写入）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shopify_admin.models.base import Base


class TaskResult(Base):
    __tablename__ = "task_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(255), index=True, comment="模块.函数名")
    result: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text, default=None)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    duration_s: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
