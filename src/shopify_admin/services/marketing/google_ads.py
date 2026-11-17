# -*- coding: utf-8 -*-
"""Google Ads API 服务（2026-09-09 新认证体系）。

背景（2026-09 官方变更）：
- 开发者令牌(developer token)已于 2026-09-09 全面停用，API 访问权限
  直接绑定 OAuth 凭据所在的 Google Cloud 项目（Cloud 控制台 →
  Google Ads API 概览页申请 Explorer/基本/标准权限，不再走 MCC API 中心）。
  客户端配置仍保留 developer_token 字段仅为兼容 google-ads 库加载校验，
  值会被 API 服务器忽略。
- 认证三件套 = OAuth Web 应用 client_id/client_secret + 一次性
  refresh_token（deploy/get_google_ads_refresh_token.py 本地浏览器授权
  获取，正式版同意屏幕下长期有效）。

依赖：google-ads 库懒加载（与 bmai 同模式，不进主依赖，避免服务器
无谓安装；需要时: uv sync --group ads 或 uv pip install google-ads）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select

from shopify_admin.config.settings import settings
from shopify_admin.core.database import session_scope
from shopify_admin.models.order import Order


class GoogleAdsConfigError(RuntimeError):
    """凭据/配置缺失（带中文指引）。"""


@dataclass
class GoogleAdsCreds:
    """Google Ads 凭据（.env 三件套 + 可选账户/令牌）。"""

    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    customer_id: str = ""        # 主广告账户 xxx-xxx-xxxx（verify 不需要，查询需要）
    developer_token: str = ""    # 2026-09 已停用；空则给占位值兼容库校验

    def missing(self) -> list[str]:
        return [
            k for k in ("client_id", "client_secret", "refresh_token")
            if not getattr(self, k)
        ]


def _micros(v: Any) -> float | None:
    """Google Ads 微单位 → 常规单位（int64 兼容 str/int）。"""
    try:
        return round(int(v) / 1_000_000, 2)
    except (TypeError, ValueError):
        return None


class GoogleAdsService:
    """Google Ads 连通验证 + 基础报表（同步风格，REST/MCP 共用）。"""

    _client: Any = None   # 类级单例（进程内复用；测试 fixture 重置）

    def __init__(self, creds: GoogleAdsCreds | None = None):
        self.creds = creds or GoogleAdsCreds(
            client_id=settings.google_ads_client_id,
            client_secret=settings.google_ads_client_secret,
            refresh_token=settings.google_ads_refresh_token,
            customer_id=settings.google_ads_customer_id,
            developer_token=settings.google_ads_developer_token,
        )

    # ------------------------------------------------------------------
    # 客户端
    # ------------------------------------------------------------------
    def _require_full_creds(self) -> None:
        miss = self.creds.missing()
        if miss:
            raise GoogleAdsConfigError(
                f"Google Ads 凭据不完整，缺少: {', '.join(miss)}。"
                "请在 .env 配置 GOOGLE_ADS_* 键（refresh_token 用 "
                "deploy/get_google_ads_refresh_token.py 本地授权获取）。"
            )

    def client(self):
        """GoogleAdsClient 单例（懒加载 google-ads 库）。"""
        if GoogleAdsService._client is None:
            self._require_full_creds()
            from google.ads.googleads.client import GoogleAdsClient  # 懒加载

            GoogleAdsService._client = GoogleAdsClient.load_from_dict({
                # 2026-09 后服务器忽略 developer_token；占位兼容库的必填校验
                "developer_token": self.creds.developer_token or "ignored-since-2026-09",
                "client_id": self.creds.client_id,
                "client_secret": self.creds.client_secret,
                "refresh_token": self.creds.refresh_token,
                "use_proto_plus": True,
            })
        return GoogleAdsService._client

    @staticmethod
    def _cid(customer_id: str | None) -> str:
        cid = (customer_id or "").replace("-", "").strip()
        if not cid or not cid.isdigit():
            raise GoogleAdsConfigError(
                "缺少有效广告账户 customer_id（格式 xxx-xxx-xxxx 或 10 位数字）；"
                "在 .env 配 GOOGLE_ADS_CUSTOMER_ID 或调用时传参。"
            )
        return cid

    # ------------------------------------------------------------------
    # 连通验证
    # ------------------------------------------------------------------
    def verify_connection(self) -> dict:
        """凭据预检 + list_accessible_customers（不需要 customer_id）。

        返回 {"ok": bool, "accessible_customers": [...]}；凭据缺失
        返回 missing 列表（不抛错，供面板展示），API 失败返回 error。
        """
        miss = self.creds.missing()
        if miss:
            return {
                "ok": False,
                "missing": miss,
                "hint": "在 .env 填 GOOGLE_ADS_* 三件套后重试",
            }
        try:
            cus = self.client().get_service("CustomerService")
            res = cus.list_accessible_customers()
            ids = [rn.split("/")[-1] for rn in res.resource_names]
            logger.info(f"[google-ads] 连通验证 OK，可访问账户 {len(ids)} 个")
            return {"ok": True, "accessible_customers": ids}
        except GoogleAdsConfigError:
            raise
        except Exception as e:  # 网络不通 / token 失效 / 项目权限不足
            logger.warning(f"[google-ads] 连通验证失败: {e}")
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------
    # 基础报表
    # ------------------------------------------------------------------
    def get_customer_info(self, customer_id: str | None = None) -> dict:
        """账户基础信息（名称/货币/时区/是否经理账号）。"""
        cid = self._cid(customer_id or self.creds.customer_id)
        svc = self.client().get_service("GoogleAdsService")
        query = (
            "SELECT customer.id, customer.descriptive_name, customer.currency_code, "
            "customer.time_zone, customer.manager FROM customer"
        )
        rows = list(svc.search(customer_id=cid, query=query))
        if not rows:
            return {"customer_id": cid, "found": False}
        c = rows[0].customer
        return {
            "customer_id": cid,
            "found": True,
            "descriptive_name": c.descriptive_name,
            "currency_code": c.currency_code,
            "time_zone": c.time_zone,
            "is_manager": bool(c.manager),
        }

    def list_campaigns(self, customer_id: str | None = None) -> list[dict]:
        """广告系列列表（含预算与全时段核心指标）。"""
        cid = self._cid(customer_id or self.creds.customer_id)
        svc = self.client().get_service("GoogleAdsService")
        query = (
            "SELECT campaign.id, campaign.name, campaign.status, "
            "campaign.advertising_channel_type, campaign_budget.amount_micros, "
            "metrics.cost_micros, metrics.clicks, metrics.impressions, "
            "metrics.conversions FROM campaign"
        )
        out: list[dict] = []
        for row in svc.search(customer_id=cid, query=query):
            c = row.campaign
            out.append({
                "id": str(c.id),
                "name": c.name,
                "status": getattr(c.status, "name", str(c.status)),
                "channel": getattr(
                    c.advertising_channel_type, "name", str(c.advertising_channel_type)
                ),
                "budget": _micros(row.campaign_budget.amount_micros),
                "cost": _micros(row.metrics.cost_micros),
                "clicks": int(row.metrics.clicks or 0),
                "impressions": int(row.metrics.impressions or 0),
                "conversions": float(row.metrics.conversions or 0),
            })
        return out

    # ------------------------------------------------------------------
    # 转化回传（gclid -> Google Ads，闭环 ROAS 归因）
    # ------------------------------------------------------------------
    # Google 限制：点击后 90 天内可回传转化
    _CONVERSION_WINDOW = timedelta(days=90)

    def _require_conversion_action(self) -> str:
        action = settings.google_ads_conversion_action
        if not action:
            raise GoogleAdsConfigError(
                "未配置转化动作。先在 Google Ads 后台：目标 → 转化 → 新建转化动作"
                "（类别=购买/网站），拿到资源名 customers/<id>/conversionActions/<n> "
                "填入 .env GOOGLE_ADS_CONVERSION_ACTION。"
            )
        return action

    def upload_click_conversions(
        self, conversions: list[dict], customer_id: str | None = None
    ) -> list[dict]:
        """批量回传点击转化（gclid 关联订单）。

        conversions 每项: {order_id, gclid, conversion_date_time,
        value, currency}；conversion_date_time 必须带时区偏移，如
        "2026-11-05 08:30:00+00:00"。返回逐项 {"uploaded": bool}。
        """
        if not conversions:
            return []
        cid = self._cid(customer_id or self.creds.customer_id)
        action = self._require_conversion_action()
        client = self.client()
        svc = client.get_service("ConversionUploadService")
        request = client.get_type("UploadClickConversionsRequest")
        request.customer_id = cid
        request.partial_failure = True   # 单条失败不拖垮整批
        conv_type = client.get_type("ClickConversion")
        for c in conversions:
            cv = conv_type()
            cv.gclid = c["gclid"]
            cv.conversion_action = c.get("conversion_action") or action
            cv.conversion_date_time = c["conversion_date_time"]
            cv.conversion_value = float(c["value"])
            cv.currency_code = c.get("currency") or "USD"
            request.conversions.append(cv)
        response = svc.upload_click_conversions(request=request)
        ok_gclids = {r.gclid for r in response.results}
        results = [
            {k: c[k] for k in ("order_id", "gclid")} | {"uploaded": c["gclid"] in ok_gclids}
            for c in conversions
        ]
        n_ok = sum(1 for r in results if r["uploaded"])
        logger.info(f"[google-ads] 转化回传 {n_ok}/{len(results)} 成功 customer={cid}")
        return results

    def _pending_stmt(self, store_id: int | None, limit: int):
        stmt = select(Order).where(
            Order.gclid != "",
            Order.ads_uploaded_at.is_(None),
            Order.financial_status == "paid",
            Order.is_test.is_(False),
            Order.shopify_created_at >= datetime.utcnow() - self._CONVERSION_WINDOW,
        )
        if store_id:
            stmt = stmt.where(Order.store_id == store_id)
        return stmt.order_by(Order.shopify_created_at).limit(limit)

    def pending_conversions(
        self, store_id: int | None = None, limit: int = 200
    ) -> dict:
        """待回传转化订单清单（已支付 + 有 gclid + 90 天窗口内 + 未回传）。"""
        with session_scope() as s:
            rows = s.execute(self._pending_stmt(store_id, limit)).scalars().all()
            return {
                "count": len(rows),
                "items": [
                    {
                        "order_id": r.id,
                        "store_id": r.store_id,
                        "name": r.name,
                        "gclid": r.gclid,
                        "total_price": float(r.total_price) if r.total_price is not None else None,
                        "currency": r.currency,
                        "created_at": r.shopify_created_at.isoformat() if r.shopify_created_at else None,
                    }
                    for r in rows
                ],
            }

    def upload_pending_conversions(
        self, store_id: int | None = None, limit: int = 200
    ) -> dict:
        """回传全部待回传订单并标记（幂等：成功即写 ads_uploaded_at）。"""
        with session_scope() as s:
            rows = s.execute(self._pending_stmt(store_id, limit)).scalars().all()
            if not rows:
                return {"total": 0, "uploaded": 0, "failed": []}
            id_rows = {r.id: r for r in rows}
            conversions = [
                {
                    "order_id": r.id,
                    "gclid": r.gclid,
                    # Shopify created_at 为 UTC；API 要求带偏移
                    "conversion_date_time": (
                        r.shopify_created_at.strftime("%Y-%m-%d %H:%M:%S") + "+00:00"
                        if r.shopify_created_at else None
                    ),
                    "value": float(r.total_price or 0),
                    "currency": r.currency or "USD",
                }
                for r in rows if r.shopify_created_at
            ]
            results = self.upload_click_conversions(conversions)
            now = datetime.utcnow()
            failed = []
            for item in results:
                row = id_rows.get(item["order_id"])
                if item["uploaded"] and row is not None:
                    row.ads_uploaded_at = now
                else:
                    failed.append(item)
            logger.info(
                f"[google-ads] 转化回传完成 total={len(results)} "
                f"ok={len(results) - len(failed)} failed={len(failed)}"
            )
            return {
                "total": len(results),
                "uploaded": len(results) - len(failed),
                "failed": failed,
            }
