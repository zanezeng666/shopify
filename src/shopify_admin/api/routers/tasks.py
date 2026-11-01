# -*- coding: utf-8 -*-
"""任务审计路由：执行记录查询 + 定时任务手动触发。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from shopify_admin.api.deps import DbSession, RequireApiKey
from shopify_admin.core.exceptions import NotFoundError
from shopify_admin.models.task import TaskResult

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[RequireApiKey])


@router.post("/{job_name}/run")
def run_job(job_name: str):
    """手动触发一个定时任务（同步执行，与定时调度共用 @task_record 审计）。"""
    from shopify_admin.scheduler.jobs import JOBS

    fn = JOBS.get(job_name)
    if fn is None:
        raise NotFoundError(f"未知任务: {job_name}（可用: {', '.join(JOBS)}）")
    result = fn()
    return {"job": job_name, "result": result, "available_jobs": sorted(JOBS)}


@router.get("/jobs")
def list_jobs():
    """任务注册表与 cron 配置。"""
    from shopify_admin.scheduler.jobs import JOBS, JOB_CRONS

    return {"jobs": [{"name": n, "cron": JOB_CRONS[n]} for n in sorted(JOBS)]}


@router.get("")
def list_tasks(
    db: Session = DbSession,
    task_name: str | None = None,
    ok: bool | None = None,  # True=成功 False=失败
    limit: int = Query(default=50, le=200),
):
    stmt = select(TaskResult).order_by(TaskResult.id.desc()).limit(limit)
    if task_name:
        stmt = stmt.where(TaskResult.task_name == task_name)
    if ok is not None:
        stmt = stmt.where(TaskResult.error.is_(None) if ok else TaskResult.error.is_not(None))
    rows = db.execute(stmt).scalars().all()
    return {
        "items": [
            {
                "id": r.id, "task_name": r.task_name, "success": r.error is None,
                "duration_s": float(r.duration_s) if r.duration_s is not None else None,
                "error": r.error, "result": r.result,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in rows
        ]
    }
