# -*- coding: utf-8 -*-
"""FastRite（星连 xlwms）海外仓渠道实现。

OpenAPI 形态（来自 xlwms_api SDK 反推）：
- POST {base}/v1{path}，JSON body = {"appKey", "authcode", "reqTime", "version", "data"}
- 签名 v2：data 递归不区分大小写排序 -> JSON 紧凑串 -> {appKey,data,reqTime} 按 key.lower()
  排序拼接值 -> HmacSHA256(appSecret) hexdigest
- 响应 {"code": 200, "data": [...], "message"}

端点：
- 库存   /integratedInventory/pageOpen
- 运费   /fee/trialFreight
- 出库单 /outboundOrder/create | /outboundOrder/detail | /outboundOrder/cancel
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal

import httpx
from loguru import logger

from shopify_admin.channels.base import (
    Address, ChannelInventory, ChannelOrderRef, ChannelOrderStatus,
    FulfillmentChannel, FulfillmentRequest, Parcel, ShippingQuote,
)
from shopify_admin.config.settings import settings
from shopify_admin.core.exceptions import ChannelError

_API_VERSION = "v1"

# xlwms 订单状态 -> 本系统状态
_STATUS_MAP = {
    0: "processing",   # 草稿
    2: "processing",   # 仓库处理中
    3: "shipped",      # 已出库
    4: "cancelled",    # 已取消
    5: "failed",       # 异常
    7: "failed",
}


def _sort_ci(obj):
    """递归按 key.lower() 排序（对齐 xlwms authcode v2）。"""
    if isinstance(obj, dict):
        return {k: _sort_ci(v) for k, v in sorted(obj.items(), key=lambda x: x[0].lower())}
    if isinstance(obj, list):
        return [_sort_ci(x) for x in obj]
    return obj


class FastRiteChannel(FulfillmentChannel):
    name = "fastrite"

    def __init__(self, transport: httpx.BaseTransport | None = None):
        self.base_url = settings.fastrite_api_base.rstrip("/")
        self.app_key = settings.fastrite_app_key
        self.app_secret = settings.fastrite_app_secret
        self._transport = transport
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------
    def _authcode(self, data, req_time: str) -> str:
        data_json = json.dumps(_sort_ci(data), separators=(",", ":"), ensure_ascii=False)
        tmp = {"appKey": self.app_key, "data": data_json, "reqTime": req_time}
        to_sign = "".join(tmp[k] for k in sorted(tmp.keys(), key=lambda x: x.lower()))
        return hmac.new(self.app_secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest()

    def _call(self, path: str, data) -> dict | list:
        if not (self.base_url and self.app_key and self.app_secret):
            raise ChannelError("FastRite 未配置（FASTRITE_API_BASE/APP_KEY/APP_SECRET）", channel="fastrite")
        if self._client is None:
            self._client = httpx.Client(timeout=30, transport=self._transport)
        req_time = str(int(time.time()))
        # authcode 走 query 参数；body 仅 reqTime/data/appKey（对齐 xlwms SDK 传输形态）
        params = {"authcode": self._authcode(data, req_time)}
        body = {"reqTime": req_time, "data": data, "appKey": self.app_key}
        resp = self._client.post(
            f"{self.base_url}/{_API_VERSION}{path}", params=params, json=body
        )
        if resp.status_code != 200:
            raise ChannelError(f"FastRite HTTP {resp.status_code}: {resp.text[:200]}", channel="fastrite")
        payload = resp.json()
        if payload.get("code") != 200:
            raise ChannelError(
                f"FastRite 业务错误 {payload.get('code')}: {str(payload.get('message'))[:200]}",
                channel="fastrite",
            )
        return payload.get("data")

    # ------------------------------------------------------------------
    # FulfillmentChannel 实现
    # ------------------------------------------------------------------
    def get_inventory(self, sku: str) -> ChannelInventory:
        """查询海外仓可用库存。

        pageOpen 的 sku 参数为模糊匹配（会带出相似 SKU 行），必须精确过滤
        row.sku == sku；可用量 = productStockDtl.availableAmount（散件可用）。
        """
        if not sku:
            raise ChannelError("sku 不能为空", channel="fastrite")
        payload = self._call("/integratedInventory/pageOpen", {"current": 1, "size": 50, "sku": sku})
        rows = payload.get("records", []) if isinstance(payload, dict) else (payload or [])
        total = 0
        warehouses: list[dict] = []
        for row in rows:
            if str(row.get("sku", "")) != sku:
                continue  # 模糊匹配带出的相似 SKU 行不计入
            dtl = row.get("productStockDtl") or {}
            avail = int(dtl.get("availableAmount") or 0)
            total += avail
            warehouses.append({"wh_code": row.get("whCode", ""), "available": avail})
        return ChannelInventory(channel=self.name, sku=sku, available=total, cs_id=sku,
                                raw={"warehouses": warehouses})

    def calculate_shipping(self, parcel: Parcel, dest: Address) -> list[ShippingQuote]:
        """运费试算（/fee/trialFreight）。"""
        data = {
            "countryCode": dest.country_code,
            "province": dest.province,
            "city": dest.city,
            "postCode": dest.zip,
            "weight": round(parcel.weight_g / 1000, 3) if parcel.weight_g else 0,
            "length": parcel.length_cm,
            "width": parcel.width_cm,
            "height": parcel.height_cm,
            "productList": [
                {"sku": it.get("sku", ""), "quantity": it.get("qty", 1)} for it in parcel.items
            ],
        }
        rows = self._call("/fee/trialFreight", data)
        quotes = []
        for row in rows or []:
            price = row.get("totalFee", row.get("fee"))
            quotes.append(
                ShippingQuote(
                    channel=self.name,
                    service_name=str(row.get("logisticsChannel", row.get("channelName", ""))),
                    price=Decimal(str(price)) if price is not None else Decimal("0"),
                    currency=str(row.get("currency", "USD")),
                    eta_days=row.get("agingDays") or row.get("estimateDays"),
                    raw=row,
                )
            )
        return quotes

    def submit_order(self, request: FulfillmentRequest) -> ChannelOrderRef:
        """创建出库单（人工 LMS 操作的接口化替代，字段按 detail 响应结构组装）。"""
        if not request.lines:
            raise ChannelError("下单行项为空", channel="fastrite")
        ship = request.ship_to
        data = {
            "thirdOrderNo": request.order_ref,
            "referOrderNo": request.order_ref,
            "receiver": ship.name,
            "telephone": ship.phone,
            "email": "",
            "countryRegionCode": ship.country_code,
            "province": ship.province,
            "city": ship.city,
            "postCode": ship.zip,
            "addressOne": ship.address1,
            "addressTwo": ship.address2,
            "productList": [
                {"sku": ln.sku, "quantity": ln.quantity} for ln in request.lines
            ],
            "remark": request.remark or "",
        }
        result = self._call("/outboundOrder/create", data)
        # create 返回 outboundOrderNo（或含单号的 dict）
        order_no = ""
        if isinstance(result, dict):
            order_no = str(result.get("outboundOrderNo") or result.get("orderNo") or "")
        elif isinstance(result, list) and result:
            order_no = str(result[0].get("outboundOrderNo", "") if isinstance(result[0], dict) else result[0])
        if not order_no:
            raise ChannelError(f"FastRite 下单成功但未返回单号: {str(result)[:200]}", channel="fastrite")
        logger.info(f"[fastrite] 出库单创建 {request.order_ref} -> {order_no}")
        return ChannelOrderRef(
            channel=self.name, order_id=order_no, third_order_no=request.order_ref,
            raw={"thirdOrderNo": request.order_ref},
        )

    def get_status(self, ref: ChannelOrderRef) -> ChannelOrderStatus:
        """按出库单号/第三方单号查状态与跟踪号（查询参数为列表形态）。"""
        if ref.order_id:
            data = {"outboundOrderNoList": [ref.order_id]}
        elif ref.third_order_no:
            data = {"thirdOrderNoList": [ref.third_order_no]}
        else:
            raise ChannelError("get_status 需要 order_id 或 third_order_no", channel="fastrite")
        rows = self._call("/outboundOrder/detail", data)
        if not rows:
            return ChannelOrderStatus(
                channel=self.name, status="processing",
                error_message=f"订单 {ref.order_id or ref.third_order_no} 未找到（可能尚未同步）",
            )
        # 优先取已出库/有效单
        target = rows[0]
        for row in rows:
            if row.get("status") == 3:
                target = row
                break
        status = _STATUS_MAP.get(target.get("status"), "processing")
        return ChannelOrderStatus(
            channel=self.name,
            status=status,
            tracking_number=str(target.get("logisticsTrackNo") or ""),
            tracking_company=str(target.get("logisticsCarrier") or "").upper(),
            error_message=str(target.get("exceptionDesc") or ""),
            raw=target,
        )

    def verify(self) -> bool:
        """连通性检测（低价只读调用）。"""
        try:
            self._call("/integratedInventory/pageOpen", {"current": 1, "size": 1})
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[fastrite] 连通性检测失败: {e}")
            return False
