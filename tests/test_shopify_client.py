# -*- coding: utf-8 -*-
"""Shopify 适配层客户端单测（httpx MockTransport，无真实网络）。"""
from __future__ import annotations

import httpx
import pytest

from shopify_admin.core.exceptions import ShopifyAPIError
from shopify_admin.platforms.shopify.client import ShopifyClient, StoreCredentials


def _client(handler, secret="secret123") -> ShopifyClient:
    creds = StoreCredentials(api_key="key123", api_secret=secret, domain="test.myshopify.com")
    return ShopifyClient(creds, transport=httpx.MockTransport(handler))


def test_basic_auth_and_200():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization", "")
        return httpx.Response(200, json={"shop": {"name": "Bomi"}})

    client = _client(handler)
    shop = client.verify()
    assert shop["name"] == "Bomi"
    assert "/admin/api/" in captured["url"]  # 版本路径
    assert captured["auth"].startswith("Basic ")  # 私有 app Basic 认证


def test_token_auth_when_secret_empty():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["token"] = request.headers.get("X-Shopify-Access-Token", "")
        return httpx.Response(200, json={"shop": {}})

    creds = StoreCredentials(api_key="shpat_xxx", api_secret="", domain="test.myshopify.com")
    client = ShopifyClient(creds, transport=httpx.MockTransport(handler))
    client.verify()
    assert captured["token"] == "shpat_xxx"  # access token 头


def test_429_retry_then_success(monkeypatch):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={})
        return httpx.Response(200, json={"orders": [{"id": 1}]})

    monkeypatch.setattr("shopify_admin.platforms.shopify.client.time.sleep", lambda s: None)
    client = _client(handler)
    orders = client.request("GET", "orders.json")
    assert orders["orders"][0]["id"] == 1
    assert calls["n"] == 2


def test_4xx_raises_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"errors": "[API] Invalid API key"})

    client = _client(handler)
    with pytest.raises(ShopifyAPIError) as ei:
        client.request("GET", "orders.json")
    assert ei.value.details["status"] == 401


def test_graphql_errors_raise():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"errors": [{"message": "bad query"}], "data": None})

    client = _client(handler)
    with pytest.raises(ShopifyAPIError, match="bad query"):
        client.graphql("{ shop { name } }")


def test_domain_normalization():
    creds = StoreCredentials(api_key="k", domain="https://x.myshopify.com/")
    assert creds.domain == "x.myshopify.com"
