# -*- coding: utf-8 -*-
"""Shopify Admin API 基础客户端。

职责：
- 版本头（X-Shopify-Api-Version / URL 版本段）
- 双凭据形态装配（Basic Auth / Access Token）
- 429 限流指数退避 + 5xx 重试
- REST 与 GraphQL 统一入口
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import ShopifyAPIError


@dataclass
class StoreCredentials:
    """店铺凭据（从 stores 表读取后装配）。"""

    api_key: str
    api_secret: str = ""
    domain: str = ""

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ShopifyAPIError("店铺凭据缺失 api_key")
        if not self.domain:
            raise ShopifyAPIError("店铺凭据缺失 domain")
        self.domain = self.domain.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
        # 老库存的是短名（如 bomibattery），规范化为完整 myshopify 域名
        if "." not in self.domain:
            self.domain = f"{self.domain}.myshopify.com"


class ShopifyClient:
    """同步客户端（与服务层/路由层风格一致）。"""

    def __init__(self, creds: StoreCredentials, api_version: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.creds = creds
        self.api_version = api_version or settings.shopify_api_version
        self.timeout = settings.shopify_api_timeout
        self.max_retries = settings.shopify_api_max_retries

        if creds.api_secret:
            # 老式私有 app：api_key:api_secret Basic Auth
            self._auth = httpx.BasicAuth(creds.api_key, creds.api_secret)
            self._token: str | None = None
        else:
            # 新式 Custom App：Admin API access token
            self._auth = None
            self._token = creds.api_key

        # 自定义 transport（测试桩/抓包）优先；代理仅作用于默认出网
        if transport is not None:
            self._client = httpx.Client(
                base_url=f"https://{creds.domain}/admin/api/{self.api_version}/",
                timeout=self.timeout,
                headers=self._default_headers(),
                transport=transport,
            )
        else:
            self._client = httpx.Client(
                base_url=f"https://{creds.domain}/admin/api/{self.api_version}/",
                timeout=self.timeout,
                headers=self._default_headers(),
                proxy=settings.shopify_proxy or None,
            )

    # ------------------------------------------------------------------
    def _default_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self._token:
            headers["X-Shopify-Access-Token"] = self._token
        return headers

    def _wait(self, response: httpx.Response, attempt: int) -> float:
        """计算退避等待：优先 Retry-After 头，否则指数退避（上限 8s）。"""
        retry_after = response.headers.get("Retry-After")
        try:
            return max(float(retry_after), 0.5) if retry_after else min(2.0 ** attempt, 8.0)
        except ValueError:
            return min(2.0 ** attempt, 8.0)

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """REST 请求：429/503 重试、4xx 抛 ShopifyAPIError。返回解析后的 JSON dict。"""
        attempt = 0
        while True:
            try:
                resp = self._client.request(method, path, params=params, json=json_body, auth=self._auth)
            except httpx.HTTPError as e:
                if attempt < self.max_retries:
                    wait = min(2.0 ** attempt, 8.0)
                    logger.warning(f"[shopify] 网络异常 {e}，{wait:.1f}s 后重试 ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait)
                    attempt += 1
                    continue
                raise ShopifyAPIError(f"Shopify 网络请求失败: {e}", details={"path": path}) from e

            if resp.status_code in (429, 503):
                if attempt < self.max_retries:
                    wait = self._wait(resp, attempt)
                    logger.warning(
                        f"[shopify] {resp.status_code} 限流/过载 {path}，{wait:.1f}s 后重试 "
                        f"({attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait)
                    attempt += 1
                    continue
                raise ShopifyAPIError(
                    f"Shopify 限流重试耗尽 ({resp.status_code})",
                    details={"path": path, "attempts": attempt + 1},
                )

            if resp.status_code >= 400:
                try:
                    body = resp.json()
                except Exception:
                    body = resp.text[:500]
                raise ShopifyAPIError(
                    f"Shopify API 错误 HTTP {resp.status_code}: {path}",
                    details={"status": resp.status_code, "errors": body},
                )

            if not resp.content:
                return {}
            return resp.json()

    # ------------------------------------------------------------------
    def graphql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """GraphQL 请求：检查 errors 与 throttling。返回 data 部分。"""
        attempt = 0
        while True:
            try:
                resp = self._client.post(
                    "graphql.json",
                    json={"query": query, "variables": variables or {}},
                    auth=self._auth,
                )
            except httpx.HTTPError as e:
                if attempt < self.max_retries:
                    time.sleep(min(2.0 ** attempt, 8.0))
                    attempt += 1
                    continue
                raise ShopifyAPIError(f"Shopify GraphQL 网络失败: {e}") from e

            if resp.status_code == 429:
                wait = self._wait(resp, attempt)
                logger.warning(f"[shopify] GraphQL 429，{wait:.1f}s 后重试")
                time.sleep(wait)
                attempt += 1
                if attempt > self.max_retries:
                    raise ShopifyAPIError("Shopify GraphQL 限流重试耗尽")
                continue

            if resp.status_code >= 400:
                raise ShopifyAPIError(
                    f"Shopify GraphQL HTTP {resp.status_code}",
                    details={"errors": resp.text[:500]},
                )

            payload = resp.json()

            # throttle 检查（cost-based）
            errors = payload.get("errors") or []
            throttled = any(
                e.get("extensions", {}).get("code") == "THROTTLED" for e in errors if isinstance(e, dict)
            )
            if throttled:
                cost = payload.get("extensions", {}).get("cost", {})
                desired = cost.get("requestedQueryCost", 100)
                status = cost.get("throttleStatus", {})
                currently_available = status.get("currentlyAvailable", 100)
                wait = max((desired - currently_available) / 50.0, 0.5)  # 50/s 恢复速率
                logger.warning(f"[shopify] GraphQL THROTTLED，等待 {wait:.1f}s")
                time.sleep(wait)
                attempt += 1
                if attempt > self.max_retries:
                    raise ShopifyAPIError("GraphQL throttle 重试耗尽")
                continue

            if errors:
                raise ShopifyAPIError(
                    "Shopify GraphQL 错误: " + "; ".join(str(e.get("message", e)) for e in errors),
                    details={"errors": errors},
                )
            return payload.get("data", {})

    # ------------------------------------------------------------------
    def verify(self) -> dict[str, Any]:
        """连通性检测：GET shop.json。返回店铺概要。"""
        data = self.request("GET", "shop.json")
        return data.get("shop", data)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ShopifyClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
