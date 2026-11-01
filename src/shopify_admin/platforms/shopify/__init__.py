# -*- coding: utf-8 -*-
"""Shopify 平台适配层。对上层暴露 ShopifyClient（REST+GraphQL）。

凭据两种形态自动适配：
- 老式私有 app（api_key + api_secret）：HTTP Basic Auth（迁移存量凭据即此形态）
- 新式 Custom App（仅 access token）：X-Shopify-Access-Token 头（api_secret 留空）
"""
from shopify_admin.platforms.shopify.client import ShopifyClient, StoreCredentials

__all__ = ["ShopifyClient", "StoreCredentials"]
