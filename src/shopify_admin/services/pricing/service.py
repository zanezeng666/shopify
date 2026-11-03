# -*- coding: utf-8 -*-
"""定价引擎（2026-11-04 用户拍板规则）。

定价口径（免邮模式，运费打进产品价）：
    C   产品成本 = cs_new.cs_product_price 的 dropship 价（US 仓优先，无 US 用 HK；两仓均 USD）
    F   运费成本 = cs_new.cs_shipping_rate 发货仓对应承运商（US→usps，HK→cs_usps），
        单件重量（净重优先）向上取档、超表尾取尾档，zone 取保守档（默认 zone9 最贵，
        保证任意目的地都不击穿利润底线）
    平台收款费 = 售价 × pay_rate + pay_fixed（Shopify Payments 2.9% + $0.30，参数化）

    P20 = (C + F + fixed) / (1 - 0.20 - pay_rate)    标准目标净利率 20%
    P15 = (C + F + fixed) / (1 - 0.15 - pay_rate)    利润底线 15%
    A   亚马逊参考价 = amazon.amazon_inventory 同 cs_id 自身最新快照
        （美国站 market_id=ATVPDKIKX0DER；多店取最低；最低价 < 次低价 ×
        outlier_ratio 时视为离群剔除、取次低 —— "正常的低价格"）

    有 A：final = max(P15, min(P20, A × amzn_discount))
          （既低于亚马逊又保 15% 底线；P15 兜底触发时独立站价将高于亚马逊价，
           记入 margin_risk 清单供人工决策）
    无 A：final = P20

    零售价 = final 向下取整到 .99 结尾（利润只增不减）。

停售下架：cs_product.status=0 或 cs_product_record 最新记录为
Stop Production / Delete / Stop Limit In Stock → Shopify 产品转 draft，不参与定价。
"""
from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select, text

from shopify_admin.config.settings import settings
from shopify_admin.core.database import get_cs_engine, session_scope
from shopify_admin.models.product import Product, ProductVariant
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

_CS_ID_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")

# 发货仓 → 承运商（cs_shipping_carrier：US→usps、HK→cs_usps，目的地 USA）
_ORIGIN_CARRIER = {"US": "usps", "HK": "cs_usps"}
# 亚马逊美国站 market_id（其它站数字为外币，混入会污染参考价）
_AMZN_US_MARKET = "ATVPDKIKX0DER"


@dataclass
class PriceDecision:
    """单产品定价决策（cs_id 粒度，同 cs_id 多变体同价）。"""

    cs_id: str
    stopped: bool = False
    origin: str = ""                 # 发货仓 US/HK
    cost: float | None = None        # 产品成本（dropship）
    ship_cost: float | None = None   # 运费成本（保守 zone）
    weight_g: int = 0
    amzn_ref: float | None = None    # 亚马逊参考价（去离群最低）
    p20: float | None = None
    p15: float | None = None
    price: float | None = None       # 最终零售价（.99 向下取整）
    basis: str = ""                  # formula20 | amazon_cap | floor15
    flag: str = "ok"                 # ok | margin_risk | no_cost | stopped
    margin: float | None = None      # 按 price 计的实际净利率

    def as_dict(self) -> dict[str, Any]:
        return {
            "cs_id": self.cs_id, "stopped": self.stopped, "origin": self.origin,
            "cost": self.cost, "ship_cost": self.ship_cost, "weight_g": self.weight_g,
            "amzn_ref": self.amzn_ref, "p20": self.p20, "p15": self.p15,
            "price": self.price, "basis": self.basis, "flag": self.flag,
            "margin": round(self.margin, 4) if self.margin is not None else None,
        }


@dataclass
class PricingConfig:
    """定价参数（默认取自 settings，测试可注入）。"""

    pay_rate: float = 0.029          # 收款费率（售价占比）
    pay_fixed: float = 0.30          # 收款固定费/单
    margin_std: float = 0.20         # 标准目标净利率
    margin_floor: float = 0.15       # 利润底线
    amzn_discount: float = 0.97      # 独立站价 = 亚马逊价 × 该系数（必须低一些）
    outlier_ratio: float = 0.6       # 最低价 < 次低价×该值 → 判离群取次低
    shipping_zone: int = 9           # 定价运费成本所用 zone（保守取最贵）
    default_weight_g: int = 113      # 无重量数据产品按首档计价

    @classmethod
    def from_settings(cls) -> "PricingConfig":
        return cls(
            pay_rate=settings.pricing_payment_rate,
            pay_fixed=settings.pricing_payment_fixed,
            margin_std=settings.pricing_margin_std,
            margin_floor=settings.pricing_margin_floor,
            amzn_discount=settings.pricing_amzn_discount,
            outlier_ratio=settings.pricing_amzn_outlier_ratio,
            shipping_zone=settings.pricing_shipping_zone,
            default_weight_g=settings.pricing_default_weight_g,
        )


class PricingService:
    """定价决策 + 店铺价格应用 + 停售下架。"""

    def __init__(self, store_service: StoreService | None = None):
        self._stores = store_service or StoreService()

    # ==================================================================
    # 纯函数（定价数学，测试重点）
    # ==================================================================
    @staticmethod
    def price_formula(
        cost: float, ship: float, margin: float, pay_rate: float, pay_fixed: float,
    ) -> float:
        """净利率定价：P 使 (P - C - F - P×rate - fixed) / P = margin。"""
        denom = 1.0 - margin - pay_rate
        if denom <= 0:
            raise ValueError(f"margin+pay_rate >= 1（{margin}+{pay_rate}）")
        return (cost + ship + pay_fixed) / denom

    @staticmethod
    def floor_to_99(x: float) -> float:
        """向下取整到 .99 结尾（价格硬上限场景，如亚马逊封顶）。"""
        if x < 1.99:
            return round(x, 2)
        v = math.floor(x) + 0.99
        if v > x:  # x 恰为整数（如 17.0 → 17.99 越界）再退一档
            v -= 1.0
        return round(v, 2)

    @staticmethod
    def ceil_to_99(x: float) -> float:
        """向上取整到 .99 结尾（目标价场景，利润只增不减）。

        x=23.25→23.99、x=17.0→17.99（floor(x)+0.99 恒 ≥ x，即 ≥x 的最近 .99）。
        """
        if x < 1.99:
            return round(x, 2)
        return round(math.floor(x) + 0.99, 2)

    @staticmethod
    def pick_amazon_ref(rows: list[tuple[Any, float]], outlier_ratio: float) -> float | None:
        """rows = [(add_date, price)]：取自身最新快照日的价格，去离群后取最低。"""
        if not rows:
            return None
        latest = max(r[0] for r in rows)
        prices = sorted(p for d, p in rows if d == latest and p > 0)
        if not prices:
            return None
        if len(prices) >= 2 and prices[0] < prices[1] * outlier_ratio:
            return prices[1]  # 最低价明显离群 → 正常的低价格（次低）
        return prices[0]

    @staticmethod
    def decide(
        cost: float, ship: float, amzn_ref: float | None, cfg: PricingConfig,
    ) -> dict[str, Any]:
        """定价决策：p20/p15/final(.99)/basis/flag/margin。"""
        p20 = PricingService.price_formula(cost, ship, cfg.margin_std, cfg.pay_rate, cfg.pay_fixed)
        p15 = PricingService.price_formula(cost, ship, cfg.margin_floor, cfg.pay_rate, cfg.pay_fixed)
        if amzn_ref and amzn_ref > 0:
            cap = amzn_ref * cfg.amzn_discount
            final = min(p20, cap)
            basis = "amazon_cap" if cap < p20 else "formula20"
            if final < p15:            # 封顶价击穿底线 → 保 15%（价将高于亚马逊）
                final = p15
                basis = "floor15"
                flag = "margin_risk"
            else:
                flag = "ok"
        else:
            final = p20
            basis = "formula20"
            flag = "ok"
        # 取整：cap 场景向下（不超亚马逊参考价）；目标价/保底场景向上（利润只增不减）；
        # cap 向下取整若击穿 P15 → 抬回 .99 保底价（最多略超 cap 分币级，利润底线优先）
        if basis == "amazon_cap":
            price = PricingService.floor_to_99(final)
            if price < p15:
                price = PricingService.ceil_to_99(p15)
                if price > amzn_ref * cfg.amzn_discount:
                    flag = "margin_risk"   # 保底价高于亚马逊参考线，供人工决策
        else:
            price = PricingService.ceil_to_99(final)
        margin = (price - cost - ship - price * cfg.pay_rate - cfg.pay_fixed) / price
        return {"p20": p20, "p15": p15, "price": price, "basis": basis,
                "flag": flag, "margin": margin}

    # ==================================================================
    # 数据装载（cs_new / amazon 库只读；测试可整体替换）
    # ==================================================================
    def load_cs_ids(self) -> list[str]:
        with get_cs_engine().connect() as c:
            rows = c.execute(text(
                "SELECT DISTINCT cs_id FROM cs_product "
                "WHERE cs_id IS NOT NULL AND cs_id <> ''")).all()
        return sorted(r[0] for r in rows)

    def load_costs(self) -> dict[str, tuple[float, str]]:
        """cs_id -> (dropship 成本, 发货仓)。US 仓优先，无 US 用 HK（均 USD）。"""
        with get_cs_engine().connect() as c:
            rows = c.execute(text(
                "SELECT cs_id, location, current_price FROM cs_product_price "
                "WHERE price_type='dropship' AND location IN ('US','HK') "
                "AND current_price > 0 ORDER BY cs_id, "
                "CASE location WHEN 'US' THEN 0 ELSE 1 END")).all()
        out: dict[str, tuple[float, str]] = {}
        for cs_id, loc, price in rows:
            if cs_id not in out:      # 排序后首个即最优仓（US 优先）
                out[cs_id] = (float(price), loc)
        return out

    def load_weights(self) -> dict[str, int]:
        """cs_id -> 单件重量（净重优先，毛重兜底）。"""
        with get_cs_engine().connect() as c:
            rows = c.execute(text(
                "SELECT cs_id, COALESCE(NULLIF(net_weight_g,0), gross_weight_g) "
                "FROM cs_product WHERE cs_id IS NOT NULL AND cs_id <> ''")).all()
        out = {}
        for cs_id, w in rows:
            v = int(w or 0)
            if cs_id not in out or v > out[cs_id]:   # 同 cs_id 多品牌记录取最大重量（保守）
                out[cs_id] = v
        return out

    def load_ship_table(self, zone: int) -> dict[str, list[tuple[int, float]]]:
        """carrier_code -> [(weight_g, price)]（升序），供向上取档。"""
        with get_cs_engine().connect() as c:
            rows = c.execute(text(
                "SELECT carrier_code, weight_g, price FROM cs_shipping_rate "
                "WHERE zone = :z AND carrier_code IN ('usps','cs_usps') "
                "ORDER BY carrier_code, weight_g"), {"z": zone}).all()
        table: dict[str, list[tuple[int, float]]] = {}
        for carrier, w, p in rows:
            table.setdefault(carrier, []).append((int(w), float(p)))
        return table

    @staticmethod
    def ship_fee(weight_g: int, table: list[tuple[int, float]], default_weight: int) -> float | None:
        """向上取档（首个 ≥ 总重）；超表尾取尾档；空表 None。"""
        if not table:
            return None
        w = weight_g if weight_g > 0 else default_weight
        for tw, price in table:
            if w <= tw:
                return price
        return table[-1][1]

    def load_amazon_refs(self, cfg: PricingConfig) -> dict[str, float]:
        """cs_id -> 亚马逊参考价（自身最新快照、美国站、去离群最低）。

        全量拉取 Python 侧归组：跨库 JOIN 有 collation 冲突（实测）。
        """
        with get_cs_engine().connect() as c:
            rows = c.execute(text(
                "SELECT cs_id, add_date, CAST(price AS DECIMAL(10,2)) "
                "FROM amazon.amazon_inventory "
                "WHERE cs_id IS NOT NULL AND cs_id <> '' "
                "AND market_id = :mkt AND price IS NOT NULL AND price <> ''"
            ), {"mkt": _AMZN_US_MARKET}).all()
        grouped: dict[str, list[tuple[Any, float]]] = {}
        for cs_id, d, p in rows:
            if p and float(p) > 0:
                grouped.setdefault(str(cs_id).strip(), []).append((d, float(p)))
        return {k: ref for k, v in grouped.items()
                if (ref := self.pick_amazon_ref(v, cfg.outlier_ratio)) is not None}

    def load_stopped(self) -> set[str]:
        """停售 cs_id：status=0 ∪ record 最新一条为 Stop 类。"""
        with get_cs_engine().connect() as c:
            s1 = {r[0] for r in c.execute(text(
                "SELECT DISTINCT cs_id FROM cs_product WHERE status = 0")).all()}
            s2 = {r[0] for r in c.execute(text(
                "SELECT r.cs_id FROM cs_product_record r "
                "JOIN (SELECT cs_id, MAX(id) mid FROM cs_product_record "
                "      GROUP BY cs_id) t ON t.mid = r.id "
                "WHERE r.status IN ('Stop Production','Delete','Stop Limit In Stock')"
            )).all()}
        return s1 | s2

    # ==================================================================
    # 决策构建
    # ==================================================================
    def build_decisions(self, cfg: PricingConfig | None = None) -> dict[str, PriceDecision]:
        cfg = cfg or PricingConfig.from_settings()
        stopped = self.load_stopped()
        costs = self.load_costs()
        weights = self.load_weights()
        ship_table = self.load_ship_table(cfg.shipping_zone)
        amzn = self.load_amazon_refs(cfg)

        decisions: dict[str, PriceDecision] = {}
        for cs_id in self.load_cs_ids():
            d = PriceDecision(cs_id=cs_id)
            if cs_id in stopped:
                d.stopped = True
                d.flag = "stopped"
                decisions[cs_id] = d
                continue
            cost_row = costs.get(cs_id)
            if not cost_row:
                d.flag = "no_cost"
                decisions[cs_id] = d
                continue
            d.cost, d.origin = cost_row
            d.weight_g = weights.get(cs_id, 0)
            table = ship_table.get(_ORIGIN_CARRIER.get(d.origin, ""), [])
            d.ship_cost = self.ship_fee(d.weight_g, table, cfg.default_weight_g)
            if d.ship_cost is None:
                d.flag = "no_cost"
                decisions[cs_id] = d
                continue
            d.amzn_ref = amzn.get(cs_id)
            r = self.decide(d.cost, d.ship_cost, d.amzn_ref, cfg)
            d.p20, d.p15 = r["p20"], r["p15"]
            d.price, d.basis, d.flag, d.margin = r["price"], r["basis"], r["flag"], r["margin"]
            decisions[cs_id] = d
        return decisions

    # ==================================================================
    # 店铺应用
    # ==================================================================
    @staticmethod
    def _variant_cs_ids(store_id: int) -> list[tuple[int, str, Decimal | None]]:
        """本地变体 (shopify_variant_id, sku, price)。"""
        with session_scope() as s:
            return [
                (r[0], r[1] or "", r[2])
                for r in s.execute(
                    select(ProductVariant.shopify_variant_id, ProductVariant.sku,
                           ProductVariant.price)
                    .where(ProductVariant.store_id == store_id)
                ).all()
            ]

    def recalc_store(
        self, store_id: int, decisions: dict[str, PriceDecision] | None = None,
        dry_run: bool = True, max_updates: int | None = None, use_graphql: bool = True,
    ) -> dict[str, Any]:
        """按定价决策对账店铺变体价：diff → 推送 Shopify → 本地回写。"""
        decisions = decisions if decisions is not None else self.build_decisions()
        cap = max_updates if max_updates is not None else settings.pricing_max_updates_per_run
        todo: list[tuple[int, str, float]] = []   # (vid, sku, new_price)
        unchanged = no_decision = stopped_hit = 0
        for vid, sku, cur in self._variant_cs_ids(store_id):
            m = _CS_ID_RE.match(sku)
            if not m:
                no_decision += 1
                continue
            d = decisions.get(m.group(1))
            if d is not None and d.stopped:
                stopped_hit += 1     # 价格不动（下架由 delist_stopped 负责）
                continue
            if d is None or d.price is None:
                no_decision += 1
                continue
            if cur is not None and abs(float(cur) - d.price) < 0.005:
                unchanged += 1
                continue
            todo.append((vid, sku, d.price))
        summary: dict[str, Any] = {
            "store_id": store_id, "dry_run": dry_run,
            "variants": len(todo) + unchanged + no_decision + stopped_hit,
            "to_update": len(todo), "unchanged": unchanged,
            "no_decision": no_decision, "stopped_variants": stopped_hit,
            "updated": 0, "failed": 0, "errors": [],
        }
        if dry_run or not todo:
            return summary
        # GraphQL 批量通道（每产品一次 mutation，全部待改价变体合并；REST 慢 ~50 倍仅兜底）
        ok: list[tuple[int, float]]
        if use_graphql:
            ok, gerrs = self._push_price_updates_graphql(store_id, todo)
            summary["updated"] = len(ok)
            summary["failed"] = len(todo) - len(ok)
            summary["errors"] = gerrs[:20]
            self._sync_local_prices(store_id, ok)
            summary["deferred"] = 0
            return summary
        batch = todo[:cap]
        ok = []
        client = self._stores.get_client(store_id)
        rest = ShopifyRest(client)
        try:
            for vid, sku, price in batch:
                try:
                    rest.set_variant_price(vid, price)
                    ok.append((vid, price))
                    summary["updated"] += 1
                except Exception as e:  # 单品失败不阻断
                    summary["failed"] += 1
                    if len(summary["errors"]) < 20:
                        summary["errors"].append(f"{sku}/{vid}: {str(e)[:120]}")
        finally:
            client.close()
        self._sync_local_prices(store_id, ok)
        summary["deferred"] = max(0, len(todo) - len(batch))
        return summary

    _BULK_PRICE_MUTATION = (
        "mutation PriceBulk($pid: ID!, $vs: [ProductVariantsBulkInput!]!) {"
        "  productVariantsBulkUpdate(productId: $pid, variants: $vs) {"
        "    productVariants { id price }"
        "    userErrors { field message }"
        "  }"
        "}"
    )

    def _push_price_updates_graphql(
        self, store_id: int, todo: list[tuple[int, str, float]],
    ) -> tuple[list[tuple[int, float]], list[str]]:
        """按产品分组合并调用 productVariantsBulkUpdate（每产品一次，throttle 由 client 处理）。"""
        with session_scope() as s:
            rows = s.execute(
                select(ProductVariant.shopify_variant_id, ProductVariant.shopify_product_id)
                .where(ProductVariant.store_id == store_id)).all()
        vid2pid = {r[0]: r[1] for r in rows}
        by_prod: dict[int, list[tuple[int, float]]] = {}
        for vid, _sku, price in todo:
            pid = vid2pid.get(vid)
            if pid:
                by_prod.setdefault(pid, []).append((vid, price))
        ok: list[tuple[int, float]] = []
        errs: list[str] = []
        if not by_prod:
            return ok, errs
        client = self._stores.get_client(store_id)
        dead = 0            # Shopify 端已不存在的产品（本地库陈旧引用，非错误）
        consec_fail = 0     # 连续网络级失败（熔断计数，防 30s×重试×上万产品）
        t0 = time.monotonic()
        try:
            for idx, (pid, items) in enumerate(by_prod.items(), 1):
                vinput = [{"id": f"gid://shopify/ProductVariant/{v}", "price": f"{p:.2f}"}
                          for v, p in items]
                try:
                    data = client.graphql(self._BULK_PRICE_MUTATION, {
                        "pid": f"gid://shopify/Product/{pid}", "vs": vinput})
                    consec_fail = 0
                    ue = (data.get("productVariantsBulkUpdate", {}).get("userErrors")) or []
                    if ue:
                        msgs = "; ".join(str(u.get("message")) for u in ue)
                        if "does not exist" in msgs:
                            dead += 1
                        else:
                            errs.append(f"product {pid}: {msgs[:150]}")
                    else:
                        ok.extend(items)
                except Exception as e:  # 单产品失败不阻断
                    errs.append(f"product {pid}: {str(e)[:150]}")
                    consec_fail += 1
                    if consec_fail >= 30:
                        errs.append(f"连续 {consec_fail} 个产品网络失败，熔断中止本轮"
                                    f"（已推 {len(ok)} 变体 / {idx - consec_fail} 产品）")
                        break
                if idx % 200 == 0:
                    rate = idx / (time.monotonic() - t0)
                    logger.info(
                        f"[pricing] 改价推送 {idx}/{len(by_prod)} 产品 ({rate:.1f}/s) "
                        f"变体ok={len(ok)} err={len(errs)} 死产品={dead}"
                    )
        finally:
            client.close()
        if dead:
            logger.warning(f"[pricing] {dead} 个产品 Shopify 端不存在（本地库陈旧引用），本轮跳过其改价")
        return ok, errs

    @staticmethod
    def _sync_local_prices(store_id: int, ok: list[tuple[int, float]]) -> None:
        if not ok:
            return
        now = datetime.now()
        with session_scope() as s:
            for vid, price in ok:
                var = s.execute(
                    select(ProductVariant).where(
                        ProductVariant.store_id == store_id,
                        ProductVariant.shopify_variant_id == vid)
                ).scalar_one_or_none()
                if var is not None:
                    var.price = Decimal(str(price))
                    var.shopify_updated_at = now

    def delist_stopped(
        self, store_id: int, decisions: dict[str, PriceDecision] | None = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """停售产品下架：Shopify status → draft + 本地同步。"""
        if decisions is not None:
            stopped = {k for k, d in decisions.items() if d.stopped}
        else:
            stopped = self.load_stopped()
        rows: list[tuple[int, str]] = []   # (shopify_product_id, title)
        with session_scope() as s:
            prods = s.execute(
                select(Product.shopify_product_id, Product.title)
                .where(Product.store_id == store_id, Product.status == "active")
            ).all()
            active_ids = [p[0] for p in prods]
            if active_ids:
                vid_rows = s.execute(
                    select(ProductVariant.shopify_product_id, ProductVariant.sku)
                    .where(ProductVariant.store_id == store_id)).all()
                by_prod: dict[int, list[str]] = {}
                for pid, sku in vid_rows:
                    by_prod.setdefault(pid, []).append(sku or "")
                for pid, title in prods:
                    if any((m := _CS_ID_RE.match(sku)) and m.group(1) in stopped
                           for sku in by_prod.get(pid, [])):
                        rows.append((pid, title))
        summary: dict[str, Any] = {
            "store_id": store_id, "dry_run": dry_run,
            "stopped_cs_ids": len(stopped), "to_delist": len(rows),
            "delisted": 0, "failed": 0, "errors": [], "items": [
                {"shopify_product_id": pid, "title": t[:80]} for pid, t in rows[:50]],
        }
        if dry_run or not rows:
            return summary
        client = self._stores.get_client(store_id)
        rest = ShopifyRest(client)
        try:
            for pid, _t in rows:
                try:
                    rest.update_product(pid, {"status": "draft"})
                    summary["delisted"] += 1
                except Exception as e:
                    summary["failed"] += 1
                    if len(summary["errors"]) < 20:
                        summary["errors"].append(f"{pid}: {str(e)[:120]}")
        finally:
            client.close()
        if summary["delisted"]:
            with session_scope() as s:
                for pid, _t in rows:
                    prod = s.execute(
                        select(Product).where(
                            Product.store_id == store_id,
                            Product.shopify_product_id == pid)
                    ).scalar_one_or_none()
                    if prod is not None:
                        prod.status = "draft"
        return summary

    # ==================================================================
    # 汇总入口（job 用）
    # ==================================================================
    def run_all_stores(self, dry_run: bool = False) -> dict[str, Any]:
        decisions = self.build_decisions()
        stats = {
            "decisions": {
                "total": len(decisions),
                "stopped": sum(1 for d in decisions.values() if d.stopped),
                "no_cost": sum(1 for d in decisions.values() if d.flag == "no_cost"),
                "margin_risk": sum(1 for d in decisions.values() if d.flag == "margin_risk"),
                "priced": sum(1 for d in decisions.values() if d.price is not None),
                "basis": {
                    b: sum(1 for d in decisions.values() if d.basis == b)
                    for b in ("formula20", "amazon_cap", "floor15")},
            },
            "stores": [],
        }
        logger.info(
            "[pricing] decisions: {total} priced={priced} stopped={stopped} "
            "no_cost={no_cost} margin_risk={margin_risk}".format(**stats["decisions"]))
        for st in self._stores.list_stores(available_only=True):
            try:
                r = self.recalc_store(st["id"], decisions, dry_run=dry_run)
                dl = self.delist_stopped(st["id"], decisions, dry_run=dry_run)
                stats["stores"].append({
                    "store_id": st["id"], "recalc": r, "delist": {
                        k: dl[k] for k in
                        ("to_delist", "delisted", "failed")}})
            except Exception as e:  # 单店失败不阻断
                logger.warning(f"[pricing] store{st['id']} 失败: {e}")
                stats["stores"].append({"store_id": st["id"], "error": str(e)[:200]})
        return stats
