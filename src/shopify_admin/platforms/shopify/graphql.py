# -*- coding: utf-8 -*-
"""Shopify GraphQL：大报表查询 + bulk operation。

日常 CRUD 走 REST；数据量大（全量产品/订单报表）走 GraphQL bulk（异步导出 JSONL）。
"""
from __future__ import annotations

import json
import time
from typing import Any

import httpx
from loguru import logger

from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import ShopifyAPIError
from shopify_admin.platforms.shopify.client import ShopifyClient

# 常用查询片段
ORDER_FIELDS = """
  id
  name
  createdAt
  processedAt
  cancelledAt
 closedAt
  displayFinancialStatus
  displayFulfillmentStatus
  totalPriceSet { shopMoney { amount currencyCode } }
  tags
  customer { email phone }
"""

# 注意：外层用 ''' 定界——GraphQL bulk 的 query 参数内部含 """（GraphQL 多行字符串语法）
BULK_ORDERS_MUTATION = '''
mutation bulkOrderReport($query: String) {
  bulkOperationRunQuery(
    query: """
    {
      orders(query: $query) {
        edges {
          node {
            id
            name
            createdAt
            processedAt
            cancelledAt
            totalPriceSet { shopMoney { amount currencyCode } }
            displayFinancialStatus
            displayFulfillmentStatus
            tags
            lineItems {
              edges {
                node {
                  id
                  name
                  sku
                  quantity
                  discountedTotalSet { shopMoney { amount currencyCode } }
                }
              }
            }
          }
        }
      }
    }
  """
  ) {
    bulkOperation {
      id
      status
    }
    userErrors {
      field
      message
    }
  }
}
'''


class ShopifyGraphQL:
    def __init__(self, client: ShopifyClient):
        self.client = client

    # ------------------------------------------------------------------
    def run_bulk(self, mutation: str, variables: dict[str, Any] | None = None,
                 poll_interval_s: float = 5.0, timeout_s: float = 600.0) -> list[dict[str, Any]]:
        """执行 bulk mutation 并轮询至完成，下载 JSONL 解析为 dict 列表。"""
        data = self.client.graphql(mutation, variables)
        op = data.get("bulkOperationRunQuery", {})
        errs = op.get("userErrors") or []
        if errs:
            raise ShopifyAPIError(f"bulk 启动失败: {errs}", details={"errors": errs})

        t0 = time.monotonic()
        url: str | None = None
        while time.monotonic() - t0 < timeout_s:
            status_data = self.client.graphql(
                "{ currentBulkOperation { id status errorCode objectCount url } }"
            )
            cur = status_data.get("currentBulkOperation", {})
            status = cur.get("status")
            logger.debug(f"[shopify] bulk 状态: {status} ({cur.get('objectCount')} objects)")
            if status == "COMPLETED":
                url = cur.get("url")
                break
            if status == "FAILED":
                raise ShopifyAPIError(
                    f"bulk 执行失败: {cur.get('errorCode')}",
                    details={"operation": cur.get("id")},
                )
            time.sleep(poll_interval_s)
        if not url:
            raise ShopifyAPIError(f"bulk 轮询超时 ({timeout_s}s)")

        return self._download_jsonl(url)

    @staticmethod
    def _download_jsonl(url: str) -> list[dict[str, Any]]:
        """下载 bulk 结果 JSONL（每行一个 JSON 对象，父子行用 __parentId 关联）。"""
        rows: list[dict[str, Any]] = []
        with httpx.Client(timeout=120, proxy=settings.shopify_proxy or None) as dl:
            with dl.stream("GET", url) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    line = line.strip()
                    if line:
                        rows.append(json.loads(line))
        return rows

    # ------------------------------------------------------------------
    def bulk_orders(self, query: str | None = None) -> list[dict[str, Any]]:
        """订单全量报表（JSONL 行含订单与行项父子关系）。"""
        return self.run_bulk(BULK_ORDERS_MUTATION, {"query": query} if query else None)
