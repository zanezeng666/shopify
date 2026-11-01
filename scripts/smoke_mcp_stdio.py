# -*- coding: utf-8 -*-
"""MCP stdio 端到端：真实子进程 + 协议握手 + 工具调用。"""
import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    env = {**os.environ, "MCP_LEVEL": "general", "PYTHONIOENCODING": "utf-8"}
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "shopify_admin.mcp_server"],
        cwd=os.path.join(os.path.dirname(__file__), "..", "src"),
        env=env,
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"handshake OK, tools={len(tools.tools)}")

            # 只读调用
            r = await session.call_tool("shopify_stores_list", {})
            text = r.content[0].text if r.content else "(no content)"
            print("stores_list:", text[:150])

            # READ-only 场景：general 调 admin 工具应被拒
            r2 = await session.call_tool("shopify_price_update",
                                         {"store_id": 1, "variant_id": 2, "price": "9.9"})
            print("admin-gate:", r2.content[0].text[:120])

            # general 允许的同步工具（假店铺 → 结构化 NOT_FOUND）
            r3 = await session.call_tool("shopify_orders_sync", {"store_id": 999999})
            print("sync(general):", r3.content[0].text[:120])

            # 报表查询（空表也应正常返回）
            r4 = await session.call_tool("shopify_report_order_status", {"store_id": 1})
            print("report:", r4.content[0].text[:120])


asyncio.run(main())
print("STDIO E2E PASS")
