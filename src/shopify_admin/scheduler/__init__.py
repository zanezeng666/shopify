# -*- coding: utf-8 -*-
"""APScheduler 构建：进程内托管（随 API 启停）或独立进程运行。"""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from shopify_admin.scheduler.jobs import JOBS, JOB_CRONS


def build_scheduler() -> BackgroundScheduler:
    """按 settings 中的 cron 表达式注册全部任务。"""
    sched = BackgroundScheduler()
    for name, func in JOBS.items():
        expr = JOB_CRONS[name]
        sched.add_job(
            func,
            CronTrigger.from_crontab(expr),
            id=name,
            name=name,
            coalesce=True,          # 积压合并为一次
            max_instances=1,        # 同任务不并发
            misfire_grace_time=300,  # 错过触发点 5 分钟内仍补跑
        )
    return sched
