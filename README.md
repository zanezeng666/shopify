# Shopify Admin（shopify_admin）

新一代 Shopify 多店铺管理系统：**全部功能接口化**——REST API（系统集成）+ MCP（AI 劃手直调）双入口共享同一服务层；平台（Shopify）与履约渠道（CS 供应商 / FastRite 海外仓）正交解耦。数据落全新库 `shopify_new`，与老库彻底解耦（老系统过渡期并行运行）。

## 架构

```
入口层    REST(FastAPI) / MCP(FastMCP 独立进程) / 定时任务(APScheduler 进程内)
服务层    stores / orders / products / inventory / fulfillment / finance / reports / marketing
适配层    platforms/shopify（httpx 自建，REST+GraphQL+bulk）
          channels/（FulfillmentChannel 抽象：cs=复用 bmai、fastrite=自建）
数据层    shopify_new（本工程 Alembic 管理） + cs_new/fast_rite 只读镜像（bmai/渠道侧自管）
```

关键决策：CS 代发能力以 **path 依赖复用 BMAI**（`bmai = {path = "E:/worksapce/BMAI"}`），单进程 import `bmai.supply_chain.cs_supplier` 等；履约下单去重共用 cs_new 的 `order_records`（platform=shopify）；FastRite 走 xlwms OpenAPI（appKey/secret，query 传 authcode）。

## 快速开始

```powershell
# 1. 配置
Copy-Item .env.example .env   # 按注释填写数据库/凭据/代理

# 2. 安装（uv）
uv sync

# 3. 建库 + 首版 schema
uv run python scripts/create_database.py
uv run alembic upgrade head

# 4. 老库迁移（幂等可重跑；--dry-run 预览 / --only stores,orders 指定段）
uv run python scripts/migrate/from_legacy.py
uv run python scripts/migrate/verify_migration.py   # 计数+抽样核验
uv run python scripts/migrate/verify_diff.py        # 跨库差集（完整性证明）
```

### 启动 REST API（含进程内定时任务）

```powershell
# .env: SCHEDULER_ENABLED=true 时随 API 启停（拉单/分仓/轮询/库存同步/日报，cron 可配）
uv run uvicorn shopify_admin.api.app:create_app --factory --host 127.0.0.1 --port 8000
# OpenAPI 文档: http://127.0.0.1:8000/docs   鉴权: X-API-Key 头（API_KEYS 配置后启用）
# 接口测试台:   http://127.0.0.1:8000/（自动发现全部接口、参数表单/示例 body 一键发送、健康总览、定时任务一键运行）
```

### 启动 MCP Server（独立进程）

```powershell
# stdio（本地 AI 客户端；权限由 MCP_LEVEL=READ|GENERAL|ADMIN 定级）
$env:MCP_LEVEL="GENERAL"; uv run python -m shopify_admin.mcp_server

# SSE（远程；MCP_TOKENS 配置 token=级别 映射，请求带 X-MCP-Token 头）
uv run python -m shopify_admin.mcp_server --sse --port 8101
```

42 个 `shopify_*` 工具覆盖八业务域；只读工具（查询/报表）READ 即可，同步类（拉单/改价/库存）需 GENERAL，写操作（下单/删除）需 ADMIN。

### 独立调度进程（可选，与 API 分离部署时）

```powershell
uv run python -m shopify_admin.scheduler
```

## 定时任务

| 任务 | cron 默认 | 说明 |
|---|---|---|
| pull_orders | `*/10 * * * *` | 可用店铺增量拉单（游标续传） |
| auto_fulfill | `*/15 * * * *` | pending 订单分仓路由；`SCHEDULER_AUTO_SUBMIT=true` 才自动下单（legacy 迁移单跳过） |
| poll_channels | `*/30 * * * *` | 渠道状态轮询 + 跟踪号回传 Shopify |
| sync_inventory | `0 * * * *` | CS/FastRite 镜像 → diff 预筛 → 限流推送 Shopify（单轮上限可配） |
| daily_report | `10 8 * * *` | 每店铺昨日销量汇总 |

手动触发：`POST /tasks/{job}/run`（与定时调度共用 `@task_record` 审计，失败 SMTP 告警）；注册表 `GET /tasks/jobs`。

## 网络要点

- 国内环境访问 `*.myshopify.com` 需代理：`.env` 配 `SHOPIFY_PROXY=http://127.0.0.1:7897`（Clash Verge mixed 端口；留空=直连）。FastRite/CS/数据库为直连，不走代理。
- 店铺 domain 支持短名（`bomibattery` 自动规范化为 `bomibattery.myshopify.com`）。

## 测试与冒烟

```powershell
uv run pytest tests/ -q                      # 34 项（渠道/服务/MCP/调度/迁移逻辑）
uv run python scripts/smoke_e2e.py           # 端到端：拉单→dry_run 分仓→渠道只读→轮询→REST 手动触发+审计
uv run python scripts/smoke_mcp_stdio.py     # MCP stdio 子进程协议握手 E2E
```
