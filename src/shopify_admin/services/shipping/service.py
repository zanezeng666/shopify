# -*- coding: utf-8 -*-
"""运费服务：CS 费率表（cs_new 镜像）→ Shopify 实时运费。

数据链路（bmai 维护，Excel 上传落库）：
    cs_shipping_carrier  承运商路线（usps: US→USA、cs_usps: HK→USA）
    cs_shipping_rate     费率表（carrier × weight_g × zone1-9 → price USD）
    cs_shipping_zone     美国邮编前 3 位 → zone 1-9

匹配方式：Shopify Carrier Service（承运商 API）——结账时 Shopify 回调本服务，
按购物车总重 + 目的邮编前 3 位查 CS 费率表，基数 × shipping_markup(1.2) 返回。
（REST shipping_zones 只读、GraphQL 无法建邮编粒度 zone，静态模板表达不了
 zone1-9 分区 × 重量档，实时回调是唯一保真通道。）
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger
from sqlalchemy import text

from shopify_admin.config.settings import settings
from shopify_admin.core.database import get_cs_engine

_CS_ID_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")


class ShippingRateService:
    """CS 费率查询 + 加价 + Shopify rates 组装。"""

    # ------------------------------------------------------------------
    # 查表（三个原语，测试可注入替换）
    # ------------------------------------------------------------------
    def _zone(self, zip_prefix: str) -> int | None:
        with get_cs_engine().connect() as c:
            return c.execute(
                text("SELECT zone FROM cs_shipping_zone WHERE zip_prefix = :p LIMIT 1"),
                {"p": zip_prefix},
            ).scalar()

    def _carriers(self, origin: str, dest: str) -> list[dict]:
        with get_cs_engine().connect() as c:
            rows = c.execute(text(
                "SELECT c.carrier_code, c.carrier_name FROM cs_shipping_carrier c "
                "WHERE c.origin = :o AND c.destination = :d AND c.is_active = 1 "
                "AND EXISTS (SELECT 1 FROM cs_shipping_rate r "
                "            WHERE r.carrier_code = c.carrier_code) "
                "ORDER BY c.id"), {"o": origin, "d": dest}).all()
            return [{"carrier": r[0], "name": r[1]} for r in rows]

    def _price(self, carrier_code: str, weight_g: int, zone: int) -> float | None:
        """向上取档：首个 ≥ 总重的档位；超表尾取尾档（最重档计价）。"""
        with get_cs_engine().connect() as c:
            row = c.execute(text(
                "SELECT price FROM cs_shipping_rate "
                "WHERE carrier_code = :c AND zone = :z AND weight_g >= :w "
                "ORDER BY weight_g ASC LIMIT 1"),
                {"c": carrier_code, "z": zone, "w": weight_g}).first()
            if row:
                return float(row[0])
            row = c.execute(text(
                "SELECT price FROM cs_shipping_rate "
                "WHERE carrier_code = :c AND zone = :z "
                "ORDER BY weight_g DESC LIMIT 1"),
                {"c": carrier_code, "z": zone}).first()
            return float(row[0]) if row else None

    def _unit_weight(self, cs_id: str) -> int:
        """cs_product 单件重量（净重优先，同 bmai 口径）。"""
        with get_cs_engine().connect() as c:
            row = c.execute(text(
                "SELECT COALESCE(net_weight_g, gross_weight_g) FROM cs_product "
                "WHERE cs_id = :id LIMIT 1"), {"id": cs_id}).first()
            return int(row[0] or 0) if row else 0

    # ------------------------------------------------------------------
    # 报价
    # ------------------------------------------------------------------
    def quote_weight(
        self, total_weight_g: int, zip_code: str,
        origin: str | None = None, dest: str = "USA",
    ) -> dict[str, Any]:
        """按总重 + 邮编报价：各承运商基数与 ×markup 后的 Shopify 展示价。"""
        origin = origin or settings.shipping_origin
        zp = (zip_code or "").strip()[:3]
        if total_weight_g <= 0:
            return {"error": "重量无效（0）", "zip_prefix": zp}
        zone = self._zone(zp)
        if zone is None:
            return {"error": f"邮编 {zip_code} 无法匹配分区（前缀 {zp} 无记录）",
                    "zip_prefix": zp}
        carriers = []
        for c in self._carriers(origin, dest):
            base = self._price(c["carrier"], total_weight_g, zone)
            if base is None:
                continue
            carriers.append({
                "carrier": c["carrier"], "name": c["name"],
                "base_price": round(base, 2),
                "price": round(base * settings.shipping_markup, 2),   # 基数 ×20%
            })
        return {
            "total_weight_g": total_weight_g, "zone": zone,
            "zip_prefix": zp, "origin": origin, "destination": dest,
            "markup": settings.shipping_markup,
            "carriers": sorted(carriers, key=lambda x: x["price"]),
        }

    def shopify_rates(self, items: list[dict], destination: dict) -> list[dict]:
        """Shopify Carrier Service 回调组装：items+destination → rates 数组。

        total_price 单位为分（cents）；非美国目的地返回空（无可用报价）。
        """
        country = (destination.get("country") or "").upper()
        if country not in ("US", "USA", "UNITED STATES"):
            return []
        total = self._cart_weight_g(items)
        if total <= 0:
            return []
        q = self.quote_weight(total, destination.get("postal_code") or "")
        if "error" in q:
            logger.warning(f"[shipping] 回调报价失败: {q['error']}")
            return []
        return [
            {
                "service_name": c["name"],
                "service_code": c["carrier"],
                "description": f"Zone {q['zone']}, {q['total_weight_g']}g",
                "currency": "USD",
                "total_price": str(int(round(c["price"] * 100))),
            }
            for c in q["carriers"]
        ]

    def _cart_weight_g(self, items: list[dict]) -> int:
        """购物车总重：item.grams 优先（建品已对齐 CS 毛重），缺失回退查库。"""
        total = 0
        for it in items:
            qty = int(it.get("quantity") or 1)
            grams = int(it.get("grams") or 0)
            if grams <= 0:
                m = _CS_ID_RE.match(str(it.get("sku") or ""))
                if m:
                    grams = self._unit_weight(m.group(1))
            total += grams * qty
        return total
