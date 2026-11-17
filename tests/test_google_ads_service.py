# -*- coding: utf-8 -*-
"""Google Ads 服务测试：凭据预检 / customer_id 规范化 / 连通验证 / 报表解析。

全桩 google-ads 库（monkeypatch sys.modules 整条包链），无需安装真库
（本地 .venv 损坏 + 服务器未装 ads 组也能跑）。
"""
from __future__ import annotations

import sys
import types
from types import SimpleNamespace

import pytest

from shopify_admin.services.marketing.google_ads import (
    GoogleAdsConfigError,
    GoogleAdsCreds,
    GoogleAdsService,
)

CREDS = GoogleAdsCreds(
    client_id="cid.apps.googleusercontent.com",
    client_secret="GOCSPX-xxx",
    refresh_token="1//rt",
    customer_id="123-456-7890",
)


@pytest.fixture(autouse=True)
def _reset_client():
    GoogleAdsService._client = None
    yield
    GoogleAdsService._client = None


@pytest.fixture()
def fake_ads_lib(monkeypatch):
    """桩 google.ads.googleads.client 包链；返回安装函数，可注入查询返回行。

    holder.loaded_configs 捕获 load_from_dict 收到的配置；
    holder.search_calls 捕获 GAQL 查询调用的 (customer_id, query)。
    """
    holder = types.SimpleNamespace(
        clients=[], loaded_configs=[], search_calls=[], rows=[]
    )

    class _FakeGoogleAdsService:
        def __init__(self):
            self._rows = holder.rows

        def search(self, customer_id, query):
            holder.search_calls.append((customer_id, query))
            return iter(self._rows)

    class _FakeCustomerService:
        def list_accessible_customers(self):
            return SimpleNamespace(
                resource_names=["customers/1111111111", "customers/2222222222"]
            )

    class _FakeClient:
        def get_service(self, name):
            if name == "CustomerService":
                return _FakeCustomerService()
            return _FakeGoogleAdsService()

    class _GoogleAdsClient:
        @staticmethod
        def load_from_dict(config):
            for k in ("client_id", "client_secret", "refresh_token", "developer_token"):
                if not config.get(k):
                    raise KeyError(k)
            holder.loaded_configs.append(dict(config))
            c = _FakeClient()
            holder.clients.append(c)
            return c

    def _install(rows=()):
        holder.rows = list(rows)
        mod = types.ModuleType("google.ads.googleads.client")
        mod.GoogleAdsClient = _GoogleAdsClient
        for name in ("google", "google.ads", "google.ads.googleads"):
            monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
        monkeypatch.setitem(sys.modules, "google.ads.googleads.client", mod)
        return holder

    return _install


def _customer_row():
    return SimpleNamespace(
        customer=SimpleNamespace(
            id="1234567890",
            descriptive_name="Estry US",
            currency_code="USD",
            time_zone="America/Los_Angeles",
            manager=False,
        )
    )


def _campaign_row():
    return SimpleNamespace(
        campaign=SimpleNamespace(
            id="1001",
            name="Search - Camera Batteries",
            status=SimpleNamespace(name="ENABLED"),
            advertising_channel_type=SimpleNamespace(name="SEARCH"),
        ),
        campaign_budget=SimpleNamespace(amount_micros="10000000"),
        metrics=SimpleNamespace(
            cost_micros="1234567",
            clicks="10",
            impressions="1000",
            conversions=1.0,
        ),
    )


# ----------------------------------------------------------------------
# 凭据预检
# ----------------------------------------------------------------------
def test_missing_creds_precheck_without_network(fake_ads_lib):
    fake_ads_lib()
    svc = GoogleAdsService(GoogleAdsCreds())
    res = svc.verify_connection()
    assert res["ok"] is False
    assert res["missing"] == ["client_id", "client_secret", "refresh_token"]
    # 未触碰 API：客户端不应建立
    assert GoogleAdsService._client is None


def test_client_raises_config_error_when_creds_incomplete():
    svc = GoogleAdsService(GoogleAdsCreds(client_id="x"))
    with pytest.raises(GoogleAdsConfigError, match="client_secret"):
        svc.client()


def test_customer_id_required_for_queries():
    svc = GoogleAdsService(GoogleAdsCreds(
        client_id="cid", client_secret="sec", refresh_token="rt", customer_id=""
    ))
    with pytest.raises(GoogleAdsConfigError, match="customer_id"):
        svc.get_customer_info()


def test_customer_id_rejects_garbage():
    svc = GoogleAdsService(GoogleAdsCreds(
        client_id="cid", client_secret="sec", refresh_token="rt", customer_id="abc"
    ))
    with pytest.raises(GoogleAdsConfigError, match="customer_id"):
        svc.list_campaigns()


# ----------------------------------------------------------------------
# 连通验证
# ----------------------------------------------------------------------
def test_verify_connection_lists_accessible(fake_ads_lib):
    fake_ads_lib()
    res = GoogleAdsService(CREDS).verify_connection()
    assert res["ok"] is True
    assert res["accessible_customers"] == ["1111111111", "2222222222"]


def test_load_from_dict_receives_creds_and_placeholder_token(fake_ads_lib):
    holder = fake_ads_lib()
    GoogleAdsService(CREDS).verify_connection()
    assert holder.loaded_configs, "load_from_dict 应被调用"
    c = holder.loaded_configs[0]
    assert c["client_id"] == CREDS.client_id
    assert c["client_secret"] == CREDS.client_secret
    assert c["refresh_token"] == CREDS.refresh_token
    # developer_token 已停用（2026-09），空值时给占位兼容库的必填校验
    assert c["developer_token"] == "ignored-since-2026-09"
    assert c["use_proto_plus"] is True


# ----------------------------------------------------------------------
# 报表
# ----------------------------------------------------------------------
def test_customer_id_normalized(fake_ads_lib):
    holder = fake_ads_lib(rows=[_customer_row()])
    GoogleAdsService(CREDS).get_customer_info()
    assert holder.search_calls, "GAQL search 应被调用"
    assert holder.search_calls[0][0] == "1234567890"


def test_get_customer_info_fields(fake_ads_lib):
    fake_ads_lib(rows=[_customer_row()])
    res = GoogleAdsService(CREDS).get_customer_info()
    assert res == {
        "customer_id": "1234567890",
        "found": True,
        "descriptive_name": "Estry US",
        "currency_code": "USD",
        "time_zone": "America/Los_Angeles",
        "is_manager": False,
    }


def test_list_campaigns_parses_micros(fake_ads_lib):
    fake_ads_lib(rows=[_campaign_row()])
    rows = GoogleAdsService(CREDS).list_campaigns()
    assert len(rows) == 1
    r = rows[0]
    assert r["id"] == "1001"
    assert r["name"] == "Search - Camera Batteries"
    assert r["status"] == "ENABLED"
    assert r["channel"] == "SEARCH"
    assert r["budget"] == 10.0            # 10_000_000 微单位
    assert r["cost"] == 1.23              # 1_234_567 微单位
    assert r["clicks"] == 10
    assert r["impressions"] == 1000
    assert r["conversions"] == 1.0


def test_get_customer_info_no_rows(fake_ads_lib):
    fake_ads_lib(rows=[])
    res = GoogleAdsService(CREDS).get_customer_info()
    assert res == {"customer_id": "1234567890", "found": False}
