# -*- coding: utf-8 -*-
"""MCP Server 冒烟：工具注册完整性 + 权限门控 + 工具 schema 生成。"""
import sys

sys.path.insert(0, "src")

from shopify_admin.mcp.permission import Permission, init_from_env, set_request_level
from shopify_admin.mcp_server import build_server

srv = build_server()

import asyncio


async def main():
    tools = await srv.list_tools()
    print(f"registered tools: {len(tools)}")
    names = sorted(t.name for t in tools)
    for n in names:
        print(" -", n)

    # schema 抽查：参数注解是否正确推断
    by_name = {t.name: t for t in tools}
    assert "shopify_orders_sync" in by_name, "缺少拉单工具"
    assert by_name["shopify_orders_sync"].inputSchema.get("required") == ["store_id"], (
        f"schema 推断异常: {by_name['shopify_orders_sync'].inputSchema}"
    )
    assert "shopify_google_field_upsert" in by_name
    props = by_name["shopify_google_field_upsert"].inputSchema.get("properties", {})
    assert "custom_label0" in props, "google 字段展开失败"
    assert "shopify_fulfillment_submit" in by_name

    # 权限门控：READ 下写工具应拒绝
    set_request_level(Permission.READ)
    import shopify_admin.mcp.tools as T
    r = T.shopify_price_update(1, 2, "9.99")
    assert "error" in r and "权限不足" in r["error"], f"READ 门控失效: {r}"
    print("READ gate OK:", r["error"][:40])

    set_request_level(Permission.ADMIN)
    r2 = T.shopify_orders_list(store_id=999999)
    print("ADMIN query:", str(r2)[:120])


asyncio.run(main())
print("SMOKE PASS")
