# -*- coding: utf-8 -*-
"""CS 供应商渠道——bmai 薄封装（platform="shopify"）。

复用 bmai 组件：
- CIMClient(rcustomerno)          CIM 认证 + HTTP（token 自动刷新）
- SkuResolver(store_name)         SKU -> CSID（正则 CS-[A-Z0-9]+ 优先，sku_csid 白名单兜底）
- map_country / map_state         地址规范映射
- cs_engine(cs_new)               本地库存/订单镜像查询（无需认证）
- OrderRecorder(platform="shopify") 跨渠道下单去重台账（cs_new.order_records）

注意：bmai 的 CSFulfillment.process 硬编码 platform="amazon"，故此处按其流程
自行编排（去重->解析->地址->运输方式->dropship/create->记录），语义对齐。
"""
from __future__ import annotations

from decimal import Decimal

from loguru import logger

from shopify_admin.channels.base import (
    Address, ChannelInventory, ChannelOrderRef, ChannelOrderStatus,
    FulfillmentChannel, FulfillmentRequest, Parcel, ShippingQuote,
)
from shopify_admin.core.exceptions import ChannelError, RouteError


class CsChannel(FulfillmentChannel):
    name = "cs"

    def __init__(self, rcustomerno: str = "", store_name: str = ""):
        self.rcustomerno = str(rcustomerno or "").strip()
        self.store_name = store_name
        self._resolver = None
        self._client = None

    # ------------------------------------------------------------------
    def _sku_to_csid(self, sku: str) -> str:
        if not sku:
            raise RouteError("SKU 为空，无法解析 CSID")
        if self._resolver is None:
            from bmai.services.fulfillment.cs.sku_resolver import SkuResolver

            self._resolver = SkuResolver(self.store_name)
        cs_id = self._resolver.resolve(sku)
        if not cs_id:
            raise RouteError(f"SKU 无法解析为 CSID: {sku}（正则与白名单均未命中）")
        return cs_id

    def _cim(self):
        if not self.rcustomerno:
            raise ChannelError("CS 渠道缺少 rcustomerno（店铺未配置 CS 客户编号）", channel="cs")
        if self._client is None:
            from bmai.supply_chain.cs_supplier import CIMClient

            self._client = CIMClient(self.rcustomerno)
        return self._client

    # ------------------------------------------------------------------
    # FulfillmentChannel 实现
    # ------------------------------------------------------------------
    def get_inventory(self, sku: str) -> ChannelInventory:
        """查 CS 本地库存镜像（cs_new.cs_inventory，按仓位聚合）。"""
        from bmai.core.database import cs_engine

        cs_id = self._sku_to_csid(sku)
        r = cs_engine.execute(
            "SELECT location, quantity FROM cs_inventory WHERE cs_id = :cs_id",
            {"cs_id": cs_id},
        )
        by_location: dict[str, int] = {}
        if r is not None:
            for row in r.fetchall():
                by_location[row[0]] = int(row[1] or 0)
        return ChannelInventory(
            channel=self.name,
            sku=sku,
            cs_id=cs_id,
            available=sum(by_location.values()),
            raw={"locations": by_location},
        )

    def calculate_shipping(self, parcel: Parcel, dest: Address) -> list[ShippingQuote]:
        """CS 无公开运费试算接口——运费比价由 FastRite 渠道提供。"""
        return []

    def submit_order(self, request: FulfillmentRequest) -> ChannelOrderRef:
        """CS dropship 代发下单（单行项一单，多行项逐行提交）。

        request.order_ref = Shopify 订单号（name，如 #1234）
        lines[i].cs_id 可预置，缺省时经 SkuResolver 解析。
        """
        from bmai.services.fulfillment.cs.address_maps import map_country, map_state
        from bmai.services.fulfillment.recorder import OrderRecorder

        if len(request.lines) != 1:
            raise ChannelError("CS 渠道一次下单仅支持单行项（逐行项编排由履约服务负责）", channel="cs")
        line = request.lines[0]
        cs_id = line.cs_id or self._sku_to_csid(line.sku)
        order_item_id = line.order_item_id

        recorder = OrderRecorder()
        if order_item_id and recorder.duplicate_exists(request.order_ref, order_item_id, platform="shopify"):
            raise ChannelError(
                f"重复下单拦截: {request.order_ref}/{order_item_id} 已存在于 order_records",
                channel="cs",
            )

        ship = request.ship_to
        country = map_country(ship.country_code)
        province = map_state(ship.province)
        ship_method = self._select_ship_method(ship.country_code, request.extra.get("main_ship_by", ""))

        data = {
            "thirdOrderId": request.order_ref,
            "csId": cs_id,
            "receiveName": ship.name,
            "receivePhone": ship.phone,
            "receiveCountry": country,
            "receiveProvince": province,
            "receiveCity": ship.city,
            "receiveAddress1": ship.address1,
            "receiveAddress2": ship.address2,
            "receiveZip": ship.zip,
            "platformOrderNo": request.order_ref,
            "platformOrderId": request.order_ref,
            "shipMethod": ship_method,
            "itemNum": line.quantity,
            "autoShip": True,
            "remark": request.remark or "shopify-admin",
        }
        resp = self._cim().post("dropship/create", data, extra_headers={"fromsystem": "shopify-admin"})
        cs_order_id = str(resp.get("dropShipId") or resp.get("id") or "")
        if not cs_order_id:
            raise ChannelError(f"CS 下单未返回单号: {str(resp)[:200]}", channel="cs")

        if order_item_id:
            recorder.record_submitted(
                request.order_ref, order_item_id, cs_id,
                platform_order_id=request.order_ref, cs_order_id=cs_order_id,
                platform="shopify", detail="shopify-admin dropship",
            )
        logger.info(f"[cs] dropship 下单 {request.order_ref}/{order_item_id} {cs_id} -> {cs_order_id}")
        return ChannelOrderRef(
            channel=self.name, order_id=cs_order_id,
            raw={"dropShipId": cs_order_id, "csId": cs_id, "shipMethod": ship_method},
        )

    def get_status(self, ref: ChannelOrderRef) -> ChannelOrderStatus:
        """查 CS 本地订单镜像（cs_new.cs_orders，bmai 同步任务维护）。"""
        from bmai.core.database import cs_engine

        r = cs_engine.execute(
            "SELECT status, tracking_no, ship_by, total_amount FROM cs_orders "
            "WHERE cs_order_id = :oid",
            {"oid": ref.order_id},
        )
        if r is None:
            return ChannelOrderStatus(channel=self.name, status="processing", error_message="查询失败")
        rows = r.fetchall()
        if not rows:
            return ChannelOrderStatus(
                channel=self.name, status="processing",
                error_message=f"CS 订单 {ref.order_id} 暂无镜像（等待同步）",
            )
        status_raw, tracking, ship_by, total = rows[0]
        status = str(status_raw or "").lower()
        if "ship" in status:  # shipped
            mapped = "shipped"
        elif status in ("cancel", "cancelled", "已取消"):
            mapped = "cancelled"
        elif status in ("error", "failed", "异常"):
            mapped = "failed"
        else:
            mapped = "processing"
        return ChannelOrderStatus(
            channel=self.name,
            status=mapped,
            tracking_number=str(tracking or ""),
            tracking_company=str(ship_by or ""),
            raw={"cs_status": status_raw, "total_amount": float(total) if total is not None else None},
        )

    def verify(self) -> bool:
        if not self.rcustomerno:
            return False
        try:
            from bmai.supply_chain.cs_supplier import get_cs_user

            get_cs_user(self.rcustomerno)
            return True
        except Exception as e:  # noqa: BLE001
            logger.warning(f"[cs] 连通性检测失败: {e}")
            return False

    # ------------------------------------------------------------------
    @staticmethod
    def _select_ship_method(country_code: str, main_ship_by: str) -> str:
        """运输方式决策（对齐 bmai CSFulfillment 的决策树）。"""
        cc = (country_code or "").upper()
        if cc == "US":
            by = (main_ship_by or "").upper()
            if by in ("UC01", "UC02", "UC03", "UC04"):
                return by
            return "UC01"  # 默认 US 标准
        if cc == "CA":
            return "UC01"
        # 其余地区（含 GB/EU/AU）
        return "UC02"
