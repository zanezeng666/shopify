# -*- coding: utf-8 -*-
"""全局配置。pydantic-settings 单例，键名与 .env 大写对应。

配置分层：
- SHOPIFY_DB_*   新库 shopify_new（主库，可写）
- LEGACY_DB_*    老库（只读，仅迁移脚本使用）
- CS_* / FASTRITE_DB_* / SMTP_*   透传给 bmai（启动时注入进程环境变量）
"""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- 新库 shopify_new（主库，可写）----
    shopify_db_host: str = ""
    shopify_db_port: int = 63698
    shopify_db_user: str = ""
    shopify_db_password: str = ""
    shopify_db_name: str = "shopify_new"
    shopify_db_charset: str = "utf8mb4"

    # ---- 老库（只读，仅迁移）----
    legacy_db_host: str = ""
    legacy_db_port: int = 63698
    legacy_db_user: str = ""
    legacy_db_password: str = ""
    legacy_db_name: str = "shopify"

    # ---- REST API 鉴权（逗号分隔，留空 = 不鉴权，仅限本地调试）----
    api_keys: str = ""

    # ---- Shopify Admin API ----
    shopify_api_version: str = "2024-10"
    shopify_api_timeout: int = 30
    shopify_api_max_retries: int = 5
    # 出网代理（国内环境访问 *.myshopify.com 通常需要；空=直连）。例 http://127.0.0.1:7897
    shopify_proxy: str = ""

    # ---- FastRite 海外仓 API ----
    fastrite_api_base: str = ""
    fastrite_app_key: str = ""
    fastrite_app_secret: str = ""

    # ---- CS 能力 API（BMAI 服务化接口，同机部署可 http://127.0.0.1:<port> 直连）----
    cs_api_base: str = ""
    cs_api_key: str = ""

    # ---- 运费同步（CS 费率表 → Shopify Carrier Service 实时回调）----
    shipping_markup: float = 1.2            # Shopify 展示运费 = CS 基数 × 该系数（+20%）
    shipping_origin: str = "US"             # 默认发货路线 origin（cs_shipping_carrier.origin，US→USA）
    shipping_callback_base_url: str = ""    # 本服务公网 HTTPS 基址（注册 carrier_service 回调用）

    # ---- 定时任务 ----
    scheduler_enabled: bool = False
    scheduler_pull_orders_cron: str = "*/10 * * * *"
    scheduler_fulfill_cron: str = "*/15 * * * *"
    scheduler_channel_poll_cron: str = "*/30 * * * *"
    scheduler_inventory_sync_cron: str = "0 * * * *"
    scheduler_reports_cron: str = "10 8 * * *"
    # 自动履约默认只分仓不下单；置 True 才自动提交渠道订单
    scheduler_auto_submit: bool = False
    # 库存同步单轮上限（首轮无缓存会全量推送，限流收敛，余量下轮继续）
    scheduler_inventory_max_per_run: int = 2000
    # 产品周同步（CS 产品库 → Shopify：发布新品 + 条码补空/重量对齐）
    scheduler_product_sync_cron: str = "0 3 * * 1"      # 每周一 03:00
    scheduler_product_sync_publish: str = "active"      # 新品发布形态 active|draft
    scheduler_product_sync_price_mode: str = "report"   # report|overwrite（定价归 pricing 引擎，此处保持 report）
    scheduler_product_sync_max_ops: int = 300           # 每店每轮创建/更新各上限（限流收敛）

    # ---- 定价引擎（2026-11-04 用户拍板；services/pricing）----
    pricing_payment_rate: float = 0.029        # 收款费率（售价占比，Shopify Payments）
    pricing_payment_fixed: float = 0.30        # 收款固定费/单
    pricing_margin_std: float = 0.20           # 标准目标净利率（扣平台收款费后）
    pricing_margin_floor: float = 0.15         # 利润底线（有亚马逊参考价封顶时）
    pricing_amzn_discount: float = 0.97        # 独立站价 = 亚马逊参考价 × 该系数
    pricing_amzn_outlier_ratio: float = 0.6    # 最低价 < 次低价×该值 → 离群剔除取次低
    pricing_shipping_zone: int = 9             # 定价运费成本 zone（保守取最贵档）
    pricing_default_weight_g: int = 113        # 无重量数据产品按首档重量计价
    pricing_max_updates_per_run: int = 1500    # 每店每轮改价上限（REST 限流收敛）
    scheduler_price_recalc_cron: str = "30 4 * * *"      # 每日 04:30 重定价+停售下架

    # ---- MCP ----
    mcp_server_name: str = "shopify-admin"
    mcp_level: str = "read"                     # stdio 模式权限级别 read|general|admin
    mcp_tokens: str = ""                        # SSE 模式令牌表 "token1:admin,token2:read"

    # ============================================================
    # bmai 透传键（与本工程 .env 同源，注入环境变量供 bmai 读取）
    # ============================================================
    cs_db_host: str = ""
    cs_db_port: int = 63698
    cs_db_user: str = ""
    cs_db_password: str = ""
    cs_db_name: str = "cs_new"
    cs_db_charset: str = "utf8"

    cs_cim_domain: str = "https://cim.cameronsino.com/admin-api/cim"
    cs_cim_auth_url: str = "https://cim.cameronsino.com/admin-api/cim/auth/login"
    cs_cim_tenant_id: str = "1"
    cs_cim_username: str = ""
    cs_cim_password: str = ""
    bmai_rcustomerno: str = ""

    fastrite_db_host: str = ""
    fastrite_db_port: int = 63698
    fastrite_db_user: str = ""
    fastrite_db_password: str = ""
    fastrite_db_name: str = "fast_rite"

    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    notify_email: str = ""

    @property
    def api_key_list(self) -> list[str]:
        """有效 API Key 列表（过滤空项）。"""
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]


# ---- bmai 环境注入 ----
# bmai 的 Settings 优先读进程环境变量（高于它自己的 env_file），
# 因此在 import bmai 之前把下列键注入 os.environ，即可用本工程 .env 驱动 bmai。
_BMAI_EXPORT_KEYS = (
    "cs_db_host", "cs_db_port", "cs_db_user", "cs_db_password",
    "cs_db_name", "cs_db_charset",
    "cs_cim_domain", "cs_cim_auth_url", "cs_cim_tenant_id",
    "cs_cim_username", "cs_cim_password", "bmai_rcustomerno",
    "fastrite_db_host", "fastrite_db_port", "fastrite_db_user",
    "fastrite_db_password", "fastrite_db_name",
    "smtp_host", "smtp_port", "smtp_user", "smtp_password", "notify_email",
)


def export_bmai_env() -> None:
    """把本工程配置的 bmai 相关键写入进程环境变量（不覆盖已有值）。"""
    for key in _BMAI_EXPORT_KEYS:
        val = getattr(settings, key, "")
        if val != "" and val is not None:
            os.environ.setdefault(key.upper(), str(val))


settings = Settings()
export_bmai_env()
