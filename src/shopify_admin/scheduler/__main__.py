# -*- coding: utf-8 -*-
"""独立调度进程：python -m shopify_admin.scheduler（不依赖 API 进程）。"""
from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler

from shopify_admin.core.logging import setup_logging
from shopify_admin.scheduler.jobs import JOBS, JOB_CRONS


def main() -> None:
    setup_logging("Logs", "INFO")
    sched = BlockingScheduler()
    for name, func in JOBS.items():
        from apscheduler.triggers.cron import CronTrigger

        sched.add_job(
            func, CronTrigger.from_crontab(JOB_CRONS[name]), id=name, name=name,
            coalesce=True, max_instances=1, misfire_grace_time=300,
        )
    print("scheduler running (Ctrl+C 退出); jobs:", ", ".join(JOBS))
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
