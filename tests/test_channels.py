# -*- coding: utf-8 -*-
"""渠道层单测：FastRite 签名/HTTP 行为 + CS 约束与决策树。"""
from __future__ import annotations

import json

import httpx
import pytest

from shopify_admin.channels.base import (
    Address, ChannelOrderRef, FulfillmentLine, FulfillmentRequest,
)
from shopify_admin.channels.cs import CsChannel
from shopify_admin.channels.fastrite import FastRiteChannel
from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import ChannelError, RouteError


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


def test_cs_no_rcustomerno_rejected():
    ch = CsChannel()
    req = FulfillmentRequest(
        order_ref="#1001", lines=[FulfillmentLine(sku="CS-TEST1", quantity=1)], ship_to=Address(),
    )
    with pytest.raises(ChannelError):
        ch.submit_order(req)


def test_cs_ship_method_decision():
    f = CsChannel._select_ship_method
    assert f("US", "") == "UC01"
    assert f("US", "uc02") == "UC02"
    assert f("CA", "") == "UC01"
    assert f("GB", "") == "UC02"
    assert f("AU", "auto") == "UC02"


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
