# -*- coding: utf-8 -*-
"""渠道层单测：FastRite 签名/HTTP 行为 + CS 约束与决策树。"""
from __future__ import annotations

import importlib.util
import json
import types

import httpx
import pytest

from shopify_admin.channels.base import (
    Address, ChannelOrderRef, FulfillmentLine, FulfillmentRequest,
)
from shopify_admin.channels.cs import CsChannel
from shopify_admin.channels.fastrite import FastRiteChannel
from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import ChannelError, RouteError

requires_bmai = pytest.mark.skipif(
    importlib.util.find_spec("bmai") is None,
    reason="CS 渠道深层链路需本地 bmai（uv pip install -e ../BMAI）",
)


# ----------------------------------------------------------------------
# FastRite 签名
# ----------------------------------------------------------------------
def test_fastrite_authcode_deterministic(monkeypatch):
    ch = FastRiteChannel(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    monkeypatch.setattr(ch, "app_key", "k1")
    monkeypatch.setattr(ch, "app_secret", "s1")
    a1 = ch._authcode({"sku": "A", "qty": 1}, "20260101000000")
    a2 = ch._authcode({"qty": 1, "sku": "A"}, "20260101000000")
    assert a1 == a2, "key 顺序不应影响签名（data 内排序后拼接）"
    assert len(a1) == 64 and all(c in "0123456789abcdef" for c in a1)


def test_fastrite_authcode_order_sensitive(monkeypatch):
    ch = FastRiteChannel(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    monkeypatch.setattr(ch, "app_key", "k1")
    monkeypatch.setattr(ch, "app_secret", "s1")
    assert ch._authcode({"a": 1}, "t1") != ch._authcode({"a": 2}, "t1")


# ----------------------------------------------------------------------
# FastRite HTTP 行为（MockTransport）
# ----------------------------------------------------------------------
def _fr(monkeypatch, handler):
    ch = FastRiteChannel(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(ch, "base_url", "https://wms.example/openapi")
    monkeypatch.setattr(ch, "app_key", "k")
    monkeypatch.setattr(ch, "app_secret", "s")
    return ch


def test_fastrite_get_inventory_aggregates(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        captured["authcode_param"] = request.url.params.get("authcode")
        return httpx.Response(200, json={"code": 200, "data": {
            "records": [
                {"sku": "SKU-1", "whCode": "US01", "productStockDtl": {"availableAmount": 3}},
                {"sku": "SKU-1", "whCode": "US02", "productStockDtl": {"availableAmount": 4}},
            ],
        }})

    inv = _fr(monkeypatch, handler).get_inventory("SKU-1")
    assert captured["path"].endswith("/integratedInventory/pageOpen")
    assert captured["body"]["appKey"] == "k"
    assert captured["authcode_param"], "authcode 应走 query 参数"
    assert inv.available == 7
    assert inv.raw["warehouses"] == [{"wh_code": "US01", "available": 3}, {"wh_code": "US02", "available": 4}]


def test_fastrite_api_error_raises(monkeypatch):
    ch = _fr(monkeypatch, lambda r: httpx.Response(200, json={"code": 500, "message": "boom"}))
    with pytest.raises(ChannelError):
        ch.get_inventory("SKU-1")


def test_fastrite_unconfigured_raises():
    ch = FastRiteChannel()  # 未注入配置（默认 settings 可能为空）
    if not (ch.app_key and ch.app_secret):
        with pytest.raises(ChannelError):
            ch.get_inventory("SKU-1")


def test_fastrite_submit_and_status(monkeypatch):
    captured_query = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/outboundOrder/create"):
            return httpx.Response(200, json={"code": 200, "data": {"outboundOrderNo": "OB123"}})
        if path.endswith("/outboundOrder/detail"):
            captured_query["body"] = json.loads(request.content)
            return httpx.Response(200, json={"code": 200, "data": [
                {"outboundOrderNo": "OB123", "status": 3,
                 "logisticsTrackNo": "1Z999", "logisticsCarrier": "ups"},
            ]})
        return httpx.Response(404)

    ch = _fr(monkeypatch, handler)
    req = FulfillmentRequest(
        order_ref="#1001",
        lines=[FulfillmentLine(sku="SKU-1", quantity=2)],
        ship_to=Address(name="John", country_code="US", city="LA", zip="90001", address1="1 Main St"),
    )
    ref = ch.submit_order(req)
    assert ref.order_id == "OB123"
    assert ref.third_order_no == "#1001"

    st = ch.get_status(ChannelOrderRef(channel="fastrite", order_id="OB123"))
    assert st.status == "shipped"
    assert st.tracking_number == "1Z999"
    assert st.tracking_company == "UPS"
    # detail 查询参数为列表形态（传输信封 {reqTime, data, appKey} 内的 data）
    assert captured_query["body"]["data"] == {"outboundOrderNoList": ["OB123"]}


def test_fastrite_status_by_third_order_no(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 200, "data": []})

    st = _fr(monkeypatch, handler).get_status(ChannelOrderRef(channel="fastrite", order_id="", third_order_no="#1001"))
    assert st.status == "processing"  # 未找到 → processing（等待同步）
    assert "未找到" in st.error_message


def test_fastrite_status_requires_ref():
    from pytest import raises

    ch = FastRiteChannel(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    with raises(ChannelError):
        ch.get_status(ChannelOrderRef(channel="fastrite", order_id=""))


# ----------------------------------------------------------------------
# CS 渠道约束
# ----------------------------------------------------------------------
def test_cs_multi_line_rejected():
    ch = CsChannel(rcustomerno="123", store_name="test")
    req = FulfillmentRequest(
        order_ref="#1001",
        lines=[FulfillmentLine(sku="A", quantity=1), FulfillmentLine(sku="B", quantity=1)],
        ship_to=Address(),
    )
    with pytest.raises(ChannelError):
        ch.submit_order(req)


@requires_bmai
def test_cs_no_rcustomerno_rejected():
    ch = CsChannel()
    req = FulfillmentRequest(
        order_ref="#1001", lines=[FulfillmentLine(sku="CS-TEST1", quantity=1)], ship_to=Address(),
    )
    with pytest.raises(ChannelError):
        ch.submit_order(req)


def _cs_api(monkeypatch, handler):
    """决策树已上收 CS API：注入 MockTransport 与配置的 CsChannel。"""
    ch = CsChannel(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(settings, "cs_api_base", "http://cs-api.test")
    monkeypatch.setattr(settings, "cs_api_key", "k1")
    return ch


def test_cs_ship_method_from_cs_api(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["country"] = request.url.params.get("country_code")
        captured["method"] = request.url.params.get("ship_method")
        captured["key"] = request.headers.get("X-API-Key")
        return httpx.Response(200, json={"country_code": "US", "ship_method": "USPS Priority Mail"})

    ch = _cs_api(monkeypatch, handler)
    assert ch._select_ship_method("US", "usps priority mail") == "USPS Priority Mail"
    assert captured["path"].endswith("/v1/fulfillment/ship-method")
    assert captured["country"] == "US"
    assert captured["method"] == "usps priority mail"
    assert captured["key"] == "k1"


def test_cs_ship_method_default_omits_param(monkeypatch):
    """缺省决策不带 ship_method 参数——老 main_ship_by（非 UC 编码）绝不进决策。

    2026-11-02 事故回归锁：main_ship_by="USPS First Class" 曾被误传为
    ship_method，导致美国订单决策端点 422 VALIDATION_ERROR、下单全挂。
    """
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.url.params.get("ship_method")
        return httpx.Response(200, json={"country_code": "US", "ship_method": "USPS"})

    ch = _cs_api(monkeypatch, handler)
    assert ch._select_ship_method("US") == "USPS"
    assert captured["method"] is None


@requires_bmai
def test_cs_submit_order_remark_contains_main_ship_by(monkeypatch):
    """submit_order：main_ship_by 拼入 CIM remark（契约语义），不进决策参数。"""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method_param"] = request.url.params.get("ship_method")
        return httpx.Response(200, json={"country_code": "US", "ship_method": "USPS"})

    ch = _cs_api(monkeypatch, handler)
    ch.rcustomerno = "123"
    monkeypatch.setattr(
        CsChannel, "_cim", lambda self: types.SimpleNamespace(
            post=lambda path, data, **kw: (
                captured.update(payload=data), {"dropShipId": "DS-1"} or {})[1]
        ),
    )

    req = FulfillmentRequest(
        order_ref="#1001",
        lines=[FulfillmentLine(sku="CS-TEST1", cs_id="CS-TEST1", quantity=1)],
        ship_to=Address(name="John", country_code="US", city="LA", zip="90001", address1="1 Main St"),
        extra={"main_ship_by": "USPS First Class"},
    )
    ref = ch.submit_order(req)
    assert ref.order_id == "DS-1"
    assert ref.raw["shipMethod"] == "USPS"
    assert captured["method_param"] is None
    assert captured["payload"]["remark"] == "shopify-admin | USPS First Class"


def test_cs_ship_method_api_error_raises(monkeypatch):
    ch = _cs_api(monkeypatch, lambda r: httpx.Response(
        502, json={"error": {"code": "CIM_UPSTREAM_ERROR"}}))
    with pytest.raises(ChannelError):
        ch._select_ship_method("US")


def test_cs_ship_method_unconfigured_raises():
    ch = CsChannel()  # 默认 settings 未配置 CS API 时应明确报错（而非静默降级）
    if not (settings.cs_api_base and settings.cs_api_key):
        with pytest.raises(ChannelError):
            ch._select_ship_method("US")


@requires_bmai
def test_cs_sku_resolve_failure(monkeypatch):
    """SkuResolver 双路未命中 -> RouteError。"""
    import types

    fake_resolver_mod = types.ModuleType("bmai.services.fulfillment.cs.sku_resolver")
    fake_resolver_mod.SkuResolver = lambda store: types.SimpleNamespace(resolve=lambda sku: None)
    import sys

    monkeypatch.setitem(sys.modules, "bmai.services.fulfillment.cs.sku_resolver", fake_resolver_mod)
    ch = CsChannel()
    with pytest.raises(RouteError):
        ch.get_inventory("NO-MATCH-SKU")
