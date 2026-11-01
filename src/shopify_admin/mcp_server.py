# -*- coding: utf-8 -*-
"""Shopify Admin MCP Server — 全部业务能力的 AI 工具入口。

启动：
    stdio（本地 AI 客户端）: uv run python -m shopify_admin.mcp_server
    SSE（远程，需令牌）    : uv run python -m shopify_admin.mcp_server --sse 8090

权限：
    stdio: 环境变量 MCP_LEVEL=read|general|admin（缺省 read）
    SSE  : 请求头 X-MCP-Token，令牌表 MCP_TOKENS="token1:admin,token2:read"

WorkBuddy/Claude 配置示例：
    {
      "mcpServers": {
        "shopify-admin": {
          "command": "uv",
          "args": ["run", "python", "-m", "shopify_admin.mcp_server"],
          "cwd": "E:\\\\worksapce\\\\shopify",
          "env": {"MCP_LEVEL": "general"}
        }
      }
    }
"""
from __future__ import annotations

import sys

from loguru import logger
from mcp.server.fastmcp import FastMCP

from shopify_admin.config.settings import settings
from shopify_admin.core.logging import setup_logging
from shopify_admin.mcp.permission import (
    Permission, init_from_env, resolve_token, set_request_level,
)
from shopify_admin.mcp.tools import ALL_TOOLS


def build_server() -> FastMCP:
    mcp = FastMCP(settings.mcp_server_name)
    for fn in ALL_TOOLS:
        mcp.add_tool(fn)
    logger.info(f"MCP: 已注册 {len(ALL_TOOLS)} 个工具")
    return mcp


mcp = build_server()


def _run_sse(port: int) -> None:
    """SSE 模式：按 X-MCP-Token 定级（未配置令牌表时只读）。"""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Mount

    class TokenLevelMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            token = request.headers.get("x-mcp-token", "")
            if token:
                level = resolve_token(token)
                if level is None:
                    return JSONResponse({"error": "无效的 MCP 令牌"}, status_code=401)
                set_request_level(level)
            else:
                set_request_level(Permission.READ)
            return await call_next(request)

    app = Starlette(
        routes=[Mount("/", app=mcp.sse_app())],
        middleware=[],
    )
    app.add_middleware(TokenLevelMiddleware)
    uvicorn.run(app, host="0.0.0.0", port=port, forwarded_allow_ips="*")


def main() -> None:
    if "--sse" in sys.argv:
        setup_logging("Logs", "INFO")
        idx = sys.argv.index("--sse")
        port = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 and sys.argv[idx + 1].isdigit() else 8090
        logger.info(f"MCP: SSE 模式 port={port}")
        _run_sse(port)
    else:
        # stdio 模式：stdout 是 JSONRPC 通道，日志必须走 stderr
        setup_logging("Logs", "INFO", console="stderr")
        init_from_env()
        logger.info("MCP: stdio 模式")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
