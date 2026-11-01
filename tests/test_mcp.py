# -*- coding: utf-8 -*-
"""MCP 层单测：权限门控、异常转换、工具注册完整性。"""
from __future__ import annotations

import pytest

from shopify_admin.core.exceptions import NotFoundError
from shopify_admin.mcp import tools as T
from shopify_admin.mcp.permission import Permission, set_request_level


@pytest.fixture(autouse=True)
def _restore_level():
    yield
    set_request_level(Permission.ADMIN)  # 测试后恢复高权限（其余测试默认可写）


def test_tool_registry_count():
    assert len(T.ALL_TOOLS) >= 40, "工具集应覆盖全部业务域（40+）"


def test_guard_converts_app_error():
    set_request_level(Permission.ADMIN)

    def boom():
        raise NotFoundError("订单不存在: 1")

    r = T._guard(boom)
    assert r == {"error": "订单不存在: 1 (NOT_FOUND)"}


def test_guard_converts_unknown_error():
    set_request_level(Permission.ADMIN)

    def boom():
        raise RuntimeError("kaboom")

    r = T._guard(boom)
    assert "内部错误" in r["error"]


def test_read_level_blocks_sync():
    set_request_level(Permission.READ)
    r = T.shopify_orders_sync(store_id=1)
    assert "权限不足" in r["error"]
    assert "GENERAL" in r["error"]


def test_read_level_blocks_admin():
    set_request_level(Permission.READ)
    assert "权限不足" in T.shopify_price_update(1, 2, "9.9")["error"]
    assert "权限不足" in T.shopify_fulfillment_submit(1)["error"]


def test_general_level_allows_sync_blocks_admin():
    set_request_level(Permission.GENERAL)
    # GENERAL 不拦截（同步会真跑——用假 store_id 拿 NOT_FOUND 结构化错误，证明未被权限拦截）
    r = T.shopify_orders_sync(store_id=999999)
    assert "权限不足" not in str(r)
    assert "权限不足" in T.shopify_price_update(1, 2, "9.9")["error"]


def test_admin_level_allows_all(monkeypatch):
    set_request_level(Permission.ADMIN)
    monkeypatch.setattr(T._products, "update_variant_price", lambda *a, **k: {"ok": True})
    r = T.shopify_price_update(1, 2, "9.9")
    assert r == {"ok": True}


def test_google_field_kwargs_filtered(monkeypatch):
    set_request_level(Permission.ADMIN)
    captured = {}

    def fake_upsert(store_id, pid, vid, **kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(T._marketing, "upsert_google_field", fake_upsert)
    T.shopify_google_field_upsert(1, 100, brand="BM", custom_label0="x", mpn=None)
    assert captured == {"brand": "BM", "custom_label0": "x"}  # None 字段被过滤


def test_server_registers_all_tools():
    from shopify_admin.mcp_server import build_server

    srv = build_server()
    names = [t.name for t in srv._tool_manager._tools.values()]
    assert "shopify_orders_sync" in names
    assert "shopify_fulfillment_submit" in names
    assert "shopify_gmc_generate" in names
