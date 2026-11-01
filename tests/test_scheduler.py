# -*- coding: utf-8 -*-
"""scheduler.jobs 单测：注册表 / auto_fulfill / sync_inventory（全部离线 stub）。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from types import SimpleNamespace

import pytest

import shopify_admin.scheduler.jobs as jobs


# ----------------------------------------------------------------------
# 注册表
# ----------------------------------------------------------------------
def test_jobs_registry_matches_crons():
    assert set(jobs.JOBS) == set(jobs.JOB_CRONS)
    for name in ("pull_orders", "auto_fulfill", "poll_channels", "sync_inventory", "daily_report", "sync_products"):
        assert name in jobs.JOBS


def test_build_scheduler_registers_all():
    from shopify_admin.scheduler import build_scheduler

    sched = build_scheduler()
    ids = {j.id for j in sched.get_jobs()}
    assert ids == set(jobs.JOBS)


# ----------------------------------------------------------------------
# auto_fulfill：legacy 过滤 + auto_submit 开关
# ----------------------------------------------------------------------
class _FakeSession:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, stmt):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeFF:
    def __init__(self):
        self.routed: list[int] = []
        self.submitted: list[int] = []

    def route_order(self, oid):
        self.routed.append(oid)

    def submit_order(self, oid):
        self.submitted.append(oid)


@pytest.mark.parametrize("auto_submit,expect_submitted", [(False, 0), (True, 2)])
def test_auto_fulfill_submit_switch(monkeypatch, auto_submit, expect_submitted):
    monkeypatch.setattr(jobs, "session_scope", lambda: _FakeSession([(11,), (12,)]))
    ff = _FakeFF()
    monkeypatch.setattr(jobs, "FulfillmentService", lambda: ff)
    monkeypatch.setattr(jobs.settings, "scheduler_auto_submit", auto_submit)
    summary = jobs.job_auto_fulfill()
    assert ff.routed == [11, 12]
    assert len(ff.submitted) == expect_submitted
    assert "routed=2" in summary
    assert f"submitted={expect_submitted}" in summary


def test_auto_fulfill_no_pending(monkeypatch):
    monkeypatch.setattr(jobs, "session_scope", lambda: _FakeSession([]))
    assert "pending=0" in jobs.job_auto_fulfill()


# ----------------------------------------------------------------------
# sync_inventory：渠道归属切分 + diff 预筛 + 单轮上限
# ----------------------------------------------------------------------
class _FakeInv:
    def __init__(self):
        self.calls: list[tuple] = []

    def diff_channel_stock(self, sid, stocks):
        self.calls.append(("diff", sid, sorted(x["sku"] for x in stocks)))
        return {"changed": stocks[:1], "unchanged": max(len(stocks) - 1, 0), "cached": 0}

    def apply_channel_stock(self, sid, todo):
        self.calls.append(("apply", sid, [x["sku"] for x in todo]))
        return SimpleNamespace(updated=len(todo), failed=0)


class _FakeStores:
    def list_stores(self, available_only=False):
        return [{"id": 7}]


def test_sync_inventory_partition_and_cap(monkeypatch):
    monkeypatch.setattr(jobs, "_load_cs_mirror", lambda: {"CS-AAA": 10, "CS-CCC": 7})
    monkeypatch.setattr(jobs, "_load_fr_mirror", lambda: {"CS-BBB": 3})
    # 变体 SKU：AAA->cs、BBB->fastrite、CCC 不在（镜像缺失跳过）、非 CS 前缀跳过
    skus = [("CS-AAA_B_1_0",), ("CS-BBB_C_2_0",), ("CS-DDD_E_3_0",), ("PLAINSKU",), (None,)]
    monkeypatch.setattr(jobs, "session_scope", lambda: _FakeSession(skus))
    monkeypatch.setattr(jobs, "StoreService", _FakeStores)
    inv = _FakeInv()
    monkeypatch.setattr(jobs, "InventoryService", lambda: inv)
    monkeypatch.setattr(jobs.settings, "scheduler_inventory_max_per_run", 5)

    summary = jobs.job_sync_inventory()

    assert inv.calls[0] == ("diff", 7, ["CS-AAA_B_1_0"])       # cs 组
    assert inv.calls[1] == ("apply", 7, ["CS-AAA_B_1_0"])      # changed 全推
    assert inv.calls[2] == ("diff", 7, ["CS-BBB_C_2_0"])       # fastrite 组
    assert inv.calls[3] == ("apply", 7, ["CS-BBB_C_2_0"])
    assert "store7" in summary
    assert "cs: match=1" in summary and "fastrite: match=1" in summary


def test_sync_inventory_no_change_no_push(monkeypatch):
    monkeypatch.setattr(jobs, "_load_cs_mirror", lambda: {"CS-AAA": 10})
    monkeypatch.setattr(jobs, "_load_fr_mirror", lambda: {})
    monkeypatch.setattr(jobs, "session_scope", lambda: _FakeSession([("CS-AAA_B_1_0",)]))
    monkeypatch.setattr(jobs, "StoreService", _FakeStores)
    inv = _FakeInv()

    class _NoChange(_FakeInv):
        def diff_channel_stock(self, sid, stocks):
            super().diff_channel_stock(sid, stocks)
            return {"changed": [], "unchanged": len(stocks), "cached": len(stocks)}

    monkeypatch.setattr(jobs, "InventoryService", lambda: _NoChange())
    summary = jobs.job_sync_inventory()
    assert "0 push" in summary
    assert all(c[0] == "diff" for c in inv.calls)


# ----------------------------------------------------------------------
# sync_products：全局镜像刷一次 + 逐店 apply + 刷新失败降级
# ----------------------------------------------------------------------
class _FakeSyncSvc:
    def __init__(self, refresh_error=None):
        self.refreshed: list[str] = []
        self.applied: list[tuple] = []
        self._refresh_error = refresh_error

    def refresh_cs_catalog(self, rno):
        self.refreshed.append(rno)
        if self._refresh_error:
            raise self._refresh_error
        return {"synced": 3, "errors": []}

    def apply(self, sid, dry_run, price_mode, publish_status, max_ops):
        self.applied.append((sid, dry_run, price_mode, publish_status, max_ops))
        return {"created": 2, "updated": 3, "skipped_existing": 1, "failed": 0}


class _StoresWithRno:
    def list_stores(self, available_only=False):
        return [{"id": 7, "rcustomerno": "R01"}, {"id": 8, "rcustomerno": ""}]


def _patch_sync_svc(monkeypatch, fake):
    import shopify_admin.services.products.sync_shopify as sync_mod

    monkeypatch.setattr(sync_mod, "CsShopifySyncService", lambda: fake)
    monkeypatch.setattr(jobs.settings, "bmai_rcustomerno", "")
    monkeypatch.setattr(jobs.settings, "scheduler_product_sync_price_mode", "report")
    monkeypatch.setattr(jobs.settings, "scheduler_product_sync_publish", "active")
    monkeypatch.setattr(jobs.settings, "scheduler_product_sync_max_ops", 300)


def test_sync_products_refresh_once_and_apply_all(monkeypatch):
    monkeypatch.setattr(jobs, "StoreService", _StoresWithRno)
    fake = _FakeSyncSvc()
    _patch_sync_svc(monkeypatch, fake)
    summary = jobs.job_sync_products()
    assert fake.refreshed == ["R01"]  # cs_product 全局镜像：只刷一次
    assert len(fake.applied) == 2
    assert fake.applied[0] == (7, False, "report", "active", 300)
    assert fake.applied[1][0] == 8
    assert "store7: +2 ~3" in summary and "store8" in summary


def test_sync_products_refresh_failure_degrades(monkeypatch):
    monkeypatch.setattr(jobs, "StoreService", _StoresWithRno)
    fake = _FakeSyncSvc(refresh_error=RuntimeError("cim down"))
    _patch_sync_svc(monkeypatch, fake)
    summary = jobs.job_sync_products()  # 刷新失败不阻断，用现有镜像继续
    assert len(fake.applied) == 2
    assert "store7: +2 ~3" in summary


def test_sync_products_no_stores(monkeypatch):
    class _NoStores:
        def list_stores(self, available_only=False):
            return []

    monkeypatch.setattr(jobs, "StoreService", _NoStores)
    fake = _FakeSyncSvc()
    _patch_sync_svc(monkeypatch, fake)
    assert jobs.job_sync_products() == "no available stores"
