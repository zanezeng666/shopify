# -*- coding: utf-8 -*-
"""Google Ads 转化闭环测试：gclid 提取 / ClickConversion 上传（全桩库）/ REST 端点。"""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from shopify_admin.config.settings import settings
from shopify_admin.services.marketing.google_ads import (
    GoogleAdsConfigError,
    GoogleAdsCreds,
    GoogleAdsService,
)
from shopify_admin.services.orders.service import _extract_gclid

CREDS = GoogleAdsCreds(
    client_id="cid", client_secret="sec", refresh_token="rt",
    customer_id="123-456-7890",
)
ACTION = "customers/1234567890/conversionActions/9"


@pytest.fixture(autouse=True)
def _reset_client():
    GoogleAdsService._client = None
    yield
    GoogleAdsService._client = None


@pytest.fixture()
def ads_lib(monkeypatch):
    """桩 google-ads 库；holder.ok_gclids 控制上传成功集合。"""
    holder = types.SimpleNamespace(ok_gclids=[], upload_requests=[])

    class _Conv:
        pass

    class _UploadRequest:
        def __init__(self):
            self.customer_id = ""
            self.partial_failure = False
            self.conversions = []

    class _ConversionUploadService:
        def upload_click_conversions(self, request):
            holder.upload_requests.append(request)
            ok = {c.gclid for c in request.conversions} & set(holder.ok_gclids)
            return SimpleNamespace(results=[SimpleNamespace(gclid=g) for g in ok])

    class _FakeClient:
        def get_service(self, name):
            assert name == "ConversionUploadService"
            return _ConversionUploadService()

        def get_type(self, name):
            if name == "UploadClickConversionsRequest":
                return _UploadRequest()
            if name == "ClickConversion":
                return _Conv
            raise AssertionError(f"未预期的 get_type: {name}")

    class _GoogleAdsClient:
        @staticmethod
        def load_from_dict(config):
            return _FakeClient()

    def _install(ok_gclids=()):
        holder.ok_gclids = list(ok_gclids)
        mod = types.ModuleType("google.ads.googleads.client")
        mod.GoogleAdsClient = _GoogleAdsClient
        for name in ("google", "google.ads", "google.ads.googleads"):
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
        monkeypatch.setitem(sys.modules, "google.ads.googleads.client", mod)
        return holder

    return _install


# ----------------------------------------------------------------------
# gclid 提取
# ----------------------------------------------------------------------
def test_extract_gclid_from_landing_site():
    o = {"landing_site": "/products/xxx?gclid=EAIaIQobChMI"}
    assert _extract_gclid(o) == "EAIaIQobChMI"


def test_extract_gclid_from_full_url():
    o = {"landing_site": "https://estry.com/collections/battery?utm_source=google&gclid=abc.def"}
    assert _extract_gclid(o) == "abc.def"


def test_extract_gclid_from_referring_site():
    o = {"referring_site": "https://google.com?a=1&gclid=xyz"}
    assert _extract_gclid(o) == "xyz"


def test_extract_gclid_missing_or_empty():
    assert _extract_gclid({}) == ""
    assert _extract_gclid({"landing_site": "/products/xxx"}) == ""
    assert _extract_gclid({"landing_site": "/products/xxx?gclid="}) == ""
    assert _extract_gclid({"landing_site": None, "referring_site": ""}) == ""


def test_extract_gclid_bad_url():
    # 坏 URL 不抛异常，回落到空
    assert _extract_gclid({"landing_site": "http://[::1/broken?gclid=zz"}) == ""


# ----------------------------------------------------------------------
# ClickConversion 上传
# ----------------------------------------------------------------------
def _convs():
    return [
        {"order_id": 1, "gclid": "g1", "conversion_date_time": "2026-11-05 08:30:00+00:00",
         "value": 29.99, "currency": "USD"},
        {"order_id": 2, "gclid": "g2", "conversion_date_time": "2026-11-05 09:00:00+00:00",
         "value": 15.0, "currency": "USD"},
    ]


def test_upload_marks_per_item_success(ads_lib, monkeypatch):
    monkeypatch.setattr(settings, "google_ads_conversion_action", ACTION)
    ads_lib(ok_gclids=["g1"])
    res = GoogleAdsService(CREDS).upload_click_conversions(_convs())
    assert res == [
        {"order_id": 1, "gclid": "g1", "uploaded": True},
        {"order_id": 2, "gclid": "g2", "uploaded": False},
    ]


def test_upload_request_shape(ads_lib, monkeypatch):
    monkeypatch.setattr(settings, "google_ads_conversion_action", ACTION)
    holder = ads_lib(ok_gclids=["g1", "g2"])
    GoogleAdsService(CREDS).upload_click_conversions(_convs())
    req = holder.upload_requests[0]
    assert req.customer_id == "1234567890"       # 连字符已规范化
    assert req.partial_failure is True
    assert len(req.conversions) == 2
    cv = req.conversions[0]
    assert cv.gclid == "g1"
    assert cv.conversion_action == ACTION
    assert cv.conversion_date_time == "2026-11-05 08:30:00+00:00"
    assert cv.conversion_value == 29.99
    assert cv.currency_code == "USD"


def test_upload_requires_conversion_action(ads_lib, monkeypatch):
    monkeypatch.setattr(settings, "google_ads_conversion_action", "")
    ads_lib()
    with pytest.raises(GoogleAdsConfigError, match="转化动作"):
        GoogleAdsService(CREDS).upload_click_conversions(_convs())


def test_upload_empty_list_is_noop(ads_lib, monkeypatch):
    monkeypatch.setattr(settings, "google_ads_conversion_action", "")
    ads_lib()
    assert GoogleAdsService(CREDS).upload_click_conversions([]) == []
    # 空批次不触达配置检查与 API


# ----------------------------------------------------------------------
# REST 端点（薄层透传）
# ----------------------------------------------------------------------
@pytest.fixture()
def client(monkeypatch):
    stub = SimpleNamespace(
        verify_connection=lambda: {"ok": True, "accessible_customers": ["7059800494"]},
        pending_conversions=lambda store_id, limit: {"count": 0, "items": []},
        upload_pending_conversions=lambda store_id, limit: {"total": 0, "uploaded": 0, "failed": []},
    )
    monkeypatch.setattr("shopify_admin.api.routers.google_ads._svc", stub)
    from shopify_admin.api.app import create_app
    return TestClient(create_app())


def test_rest_verify(client):
    r = client.get("/google-ads/verify")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "accessible_customers": ["7059800494"]}


def test_rest_conversions_pending(client):
    r = client.get("/google-ads/conversions/pending", params={"store_id": 1})
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_rest_conversions_upload(client):
    r = client.post("/google-ads/conversions/upload", json={"store_id": 1, "limit": 50})
    assert r.status_code == 200
    assert r.json()["total"] == 0
