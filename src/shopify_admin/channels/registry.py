# -*- coding: utf-8 -*-
"""渠道注册表：按名称懒加载渠道实例（带上下文缓存）。"""
from __future__ import annotations

from shopify_admin.channels.base import FulfillmentChannel
from shopify_admin.core.exceptions import NotFoundError

_cache: dict[str, FulfillmentChannel] = {}

_AVAILABLE = ("cs", "fastrite")


def get_channel(
    name: str,
    *,
    rcustomerno: str = "",
    store_name: str = "",
) -> FulfillmentChannel:
    """获取渠道实例。

    - cs 渠道下单需要 rcustomerno（店铺 CS 客户编号）与 store_name（SKU 白名单键）；
      库存/状态查询（本地镜像）可无参。
    - fastrite 渠道全局配置（.env），无需参数。
    """
    key = name.strip().lower()
    if key == "cs" and rcustomerno:
        key = f"cs:{rcustomerno}"  # 已认证实例按客户编号缓存
    if key in _cache:
        return _cache[key]
    if key == "cs":
        from shopify_admin.channels.cs import CsChannel

        _cache[key] = CsChannel(rcustomerno=rcustomerno, store_name=store_name)
    elif key == "fastrite":
        from shopify_admin.channels.fastrite import FastRiteChannel

        _cache[key] = FastRiteChannel()
    else:
        raise NotFoundError(f"未知履约渠道: {name}（可用: {', '.join(_AVAILABLE)}）")
    return _cache[key]


def available_channels() -> list[str]:
    return list(_AVAILABLE)
