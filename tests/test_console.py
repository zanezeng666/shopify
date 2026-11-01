# -*- coding: utf-8 -*-
"""接口测试台页面挂载回归：GET / 与 /console 返回自包含测试页。"""
from fastapi.testclient import TestClient

from shopify_admin.api.app import create_app


def test_console_served_at_root_and_alias():
    with TestClient(create_app()) as client:
        for path in ("/", "/console"):
            rsp = client.get(path)
            assert rsp.status_code == 200, (path, rsp.status_code)
            assert "接口测试台" in rsp.text
            assert "openapi.json" in rsp.text   # 动态发现接口的依据
            assert "text/html" in rsp.headers["content-type"]


def test_console_page_not_in_openapi_schema():
    with TestClient(create_app()) as client:
        spec = client.get("/openapi.json").json()
        assert "/console" not in spec["paths"]
        assert "/health" in spec["paths"]
