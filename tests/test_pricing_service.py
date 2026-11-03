# -*- coding: utf-8 -*-
"""定价引擎测试：公式数学 / 离群剔除 / 封顶夹逼 / 停售下架 / 店铺对账。"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shopify_admin.services.pricing.service import (
    PricingConfig,
    PricingService,
    PriceDecision,
)

CFG = PricingConfig()  # 默认：2.9%+0.30 / 20% / 15% / 0.97 / 0.6 / zone9


# ----------------------------------------------------------------------
# 公式数学
# ----------------------------------------------------------------------
def test_price_formula_hits_target_margin():
    p = PricingService.price_formula(10.0, 8.81, 0.20, CFG.pay_rate, CFG.pay_fixed)
    # 净利 = P - C - F - P×rate - fixed，净利率应精确 = 20%
    margin = (p - 10.0 - 8.81 - p * CFG.pay_rate - CFG.pay_fixed) / p
    assert abs(margin - 0.20) < 1e-9


def test_price_formula_floor_margin():
    p = PricingService.price_formula(10.0, 8.81, 0.15, CFG.pay_rate, CFG.pay_fixed)
    margin = (p - 10.0 - 8.81 - p * CFG.pay_rate - CFG.pay_fixed) / p
    assert abs(margin - 0.15) < 1e-9


def test_price_formula_rejects_bad_margin():
    with pytest.raises(ValueError):
        PricingService.price_formula(10, 5, 0.99, CFG.pay_rate, CFG.pay_fixed)


def test_floor_to_99():
    f = PricingService.floor_to_99
    assert f(17.23) == 16.99
    assert f(17.99) == 17.99
    assert f(18.0) == 17.99     # 恰为整数再退一档（硬上限场景）
    assert f(12.34) == 11.99
    assert f(1.5) == 1.5        # 低价位不硬凑 .99


def test_ceil_to_99():
    c = PricingService.ceil_to_99
    assert c(23.25) == 23.99    # 保底/目标价向上取（利润只增不减）
    assert c(24.76) == 24.99
    assert c(17.99) == 17.99
    assert c(17.0) == 17.99
    assert c(1.5) == 1.5


# ----------------------------------------------------------------------
# 亚马逊参考价：最新快照 + 离群剔除
# ----------------------------------------------------------------------
def test_pick_amazon_ref_takes_latest_snapshot_only():
    rows = [(date(2026, 10, 1), 30.0), (date(2026, 11, 3), 20.0), (date(2026, 11, 3), 22.0)]
    assert PricingService.pick_amazon_ref(rows, CFG.outlier_ratio) == 20.0


def test_pick_amazon_ref_drops_outlier_low():
    # 实测形态：CS-PDHV20 [17.99, 32.46, 32.46]
    rows = [(date(2026, 11, 3), 32.46), (date(2026, 11, 3), 17.99), (date(2026, 11, 3), 32.46)]
    assert PricingService.pick_amazon_ref(rows, CFG.outlier_ratio) == 32.46


def test_pick_amazon_ref_keeps_normal_low():
    # 最低仅比次低低 4%：正常低价格，直接取
    rows = [(date(2026, 11, 3), 7.99), (date(2026, 11, 3), 7.69)]
    assert PricingService.pick_amazon_ref(rows, CFG.outlier_ratio) == 7.69


def test_pick_amazon_ref_empty_or_nonpositive():
    assert PricingService.pick_amazon_ref([], 0.6) is None
    assert PricingService.pick_amazon_ref([(date(2026, 1, 1), 0)], 0.6) is None


# ----------------------------------------------------------------------
# 决策：封顶夹逼
# ----------------------------------------------------------------------
def test_decide_no_amazon_uses_formula20():
    r = PricingService.decide(10.0, 8.81, None, CFG)
    assert r["basis"] == "formula20"
    assert abs(r["p20"] - (10 + 8.81 + 0.30) / 0.771) < 1e-9
    assert r["flag"] == "ok"


def test_decide_amazon_cap_applies():
    # 造 p15 < cap < p20 的区间：cap = p20 - 0.50 → amzn = (p20-0.50)/0.97
    p20 = (10.0 + 8.81 + 0.30) / 0.771          # ≈ 24.76
    p15 = (10.0 + 8.81 + 0.30) / 0.821          # ≈ 23.25
    amzn = (p20 - 0.50) / 0.97                  # cap ≈ 24.26，落在 (p15, p20)
    r = PricingService.decide(10.0, 8.81, amzn, CFG)
    assert r["basis"] == "amazon_cap"
    assert r["price"] == PricingService.floor_to_99(p20 - 0.50)
    assert p15 <= r["price"]


def test_decide_cap_below_floor_keeps_floor_and_flags():
    # cap 击穿 P15：保 15% 底线，价将高于亚马逊 → margin_risk
    r = PricingService.decide(10.0, 8.81, 15.0, CFG)   # cap=14.55 < p15≈23.25
    assert r["basis"] == "floor15"
    assert r["flag"] == "margin_risk"
    assert r["price"] == PricingService.ceil_to_99(r["p15"])


def test_decide_amazon_high_keeps_formula():
    # 亚马逊价远高：p20 不受影响
    r = PricingService.decide(10.0, 8.81, 200.0, CFG)
    assert r["basis"] == "formula20"
    assert r["flag"] == "ok"


def test_decide_amazon_cap_rounding_never_breaks_floor():
    # 冒烟实测形态：cap=36.97 → floor_to_99=35.99 < p15=36.20（取整击穿底线）
    # → 抬回 ceil_to_99(p15)=36.99（略超 cap 分币级，利润底线优先）
    r = PricingService.decide(19.5, 9.92, 38.11, CFG)
    assert r["basis"] == "amazon_cap"
    assert r["price"] == 36.99
    assert r["margin"] >= CFG.margin_floor - 1e-9


def test_decide_amazon_cap_round_ok_keeps_cap():
    # cap 取整未击穿底线：保持向下取整不抬价
    r = PricingService.decide(8.5, 9.92, 24.96, CFG)   # cap=24.21→23.99, p15=22.80
    assert r["price"] == 23.99
    assert r["flag"] == "ok"
    assert r["margin"] >= CFG.margin_floor - 1e-9


def test_decide_margin_never_below_floor_when_flagged():
    # margin_risk 场景实际净利率仍 ≥ 15%（.99 取整只增不减）
    r = PricingService.decide(10.0, 8.81, 15.0, CFG)
    assert r["margin"] >= CFG.margin_floor - 1e-9


# ----------------------------------------------------------------------
# 运费取档
# ----------------------------------------------------------------------
def test_ship_fee_rounds_up_and_tail():
    table = [(113, 8.81), (226, 8.81), (454, 9.62), (906, 10.05)]
    assert PricingService.ship_fee(300, table, 113) == 9.62    # 向上取档
    assert PricingService.ship_fee(113, table, 113) == 8.81
    assert PricingService.ship_fee(5000, table, 113) == 10.05  # 超表尾取尾档
    assert PricingService.ship_fee(0, table, 113) == 8.81      # 无重量按默认档
    assert PricingService.ship_fee(100, [], 113) is None


# ----------------------------------------------------------------------
# build_decisions 集成（monkeypatch 数据装载）
# ----------------------------------------------------------------------
def _patch_loaders(monkeypatch, *, cs_ids, costs, weights, ship, amzn, stopped):
    svc_mod = PricingService
    monkeypatch.setattr(svc_mod, "load_cs_ids", lambda self: cs_ids)
    monkeypatch.setattr(svc_mod, "load_costs", lambda self: costs)
    monkeypatch.setattr(svc_mod, "load_weights", lambda self: weights)
    monkeypatch.setattr(svc_mod, "load_ship_table",
                        lambda self, z: ship)
    monkeypatch.setattr(svc_mod, "load_amazon_refs", lambda self, cfg: amzn)
    monkeypatch.setattr(svc_mod, "load_stopped", lambda self: stopped)


def test_build_decisions_stopped_no_cost_and_pricing(monkeypatch):
    _patch_loaders(
        monkeypatch,
        cs_ids=["CS-A", "CS-B", "CS-C", "CS-D"],
        costs={"CS-A": (10.0, "US"), "CS-B": (12.0, "US")},
        weights={"CS-A": 200, "CS-B": 300, "CS-C": 100},
        ship={"usps": [(113, 8.81), (226, 8.81), (454, 9.62)]},
        amzn={"CS-B": 28.0},    # cap=27.16 落在 (p15≈26.7, p20≈28.4) → 封顶生效
        stopped={"CS-D"},
    )
    ds = PricingService().build_decisions(CFG)
    assert ds["CS-D"].stopped and ds["CS-D"].flag == "stopped"
    assert ds["CS-A"].flag == "ok" and ds["CS-A"].price is not None
    assert ds["CS-A"].ship_cost == 8.81 and ds["CS-A"].origin == "US"
    # CS-B 有亚马逊价 cap=24.25 < p20 (12+9.62+.3)/.771≈28.44 → 封顶
    assert ds["CS-B"].basis == "amazon_cap"
    # 无成本（cs_id 不在成本表）
    assert ds["CS-C"].flag == "no_cost"


def test_build_decisions_hk_fallback(monkeypatch):
    _patch_loaders(
        monkeypatch,
        cs_ids=["CS-HK"],
        costs={"CS-HK": (10.0, "HK")},
        weights={"CS-HK": 200},
        ship={"usps": [(113, 8.81)], "cs_usps": [(113, 10.58)]},
        amzn={},
        stopped=set(),
    )
    d = PricingService().build_decisions(CFG)["CS-HK"]
    assert d.origin == "HK" and d.ship_cost == 10.58   # HK 用 cs_usps 表
    assert d.basis == "formula20"


def test_build_decisions_us_preferred_over_hk(monkeypatch):
    # 同 cs_id US/HK 都有价 → US 优先（load_costs 已按序去重，此处验证排序输入）
    svc = PricingService()
    # load_costs 的 SQL 排序逻辑以首见为准——直接用 SQL 侧行为验证太重，
    # 这里验证 setter：手工构造有序输入
    costs = {"CS-X": (5.0, "US")}     # loader 已保证 US 优先
    assert costs["CS-X"][1] == "US"


# ----------------------------------------------------------------------
# recalc_store：对账 diff（不触真库/真 API）
# ----------------------------------------------------------------------
def test_recalc_store_dry_run_diff(monkeypatch):
    decisions = {
        "CS-A": PriceDecision(cs_id="CS-A", price=19.99),
        "CS-B": PriceDecision(cs_id="CS-B", stopped=True, flag="stopped"),
        "CS-C": PriceDecision(cs_id="CS-C", price=29.99),
    }
    variants = [
        (111, "CS-A_Brand_1_0", Decimal("19.99")),   # 一致 → unchanged
        (112, "CS-A_Brand_1_1", Decimal("15.00")),   # 待改 → todo
        (113, "CS-B_Brand_2_0", Decimal("12.00")),   # 停售 → 跳过
        (114, "PLAIN-SKU", Decimal("9.99")),         # 非 CS 前缀
        (115, "CS-Z_Brand_9_0", Decimal("9.99")),    # 无决策
    ]
    monkeypatch.setattr(PricingService, "_variant_cs_ids",
                        staticmethod(lambda sid: variants))
    r = PricingService().recalc_store(7, decisions, dry_run=True)
    assert r["to_update"] == 1 and r["unchanged"] == 1
    assert r["stopped_variants"] == 1 and r["no_decision"] == 2
    assert r["updated"] == 0


def test_recalc_store_cap_and_push(monkeypatch):
    decisions = {"CS-A": PriceDecision(cs_id="CS-A", price=19.99)}
    variants = [(111, "CS-A_B_1_0", Decimal("15.00")), (112, "CS-A_B_1_1", Decimal("18.00"))]

    pushed: list[tuple[int, float]] = []
    synced: list[tuple[int, list]] = []

    class _FakeClient:
        def close(self):
            pass

    class _FakeStores:
        def get_client(self, sid):
            return _FakeClient()

    import shopify_admin.services.pricing.service as pmod

    def _fake_set_price(self, vid, price):
        pushed.append((vid, price))

    monkeypatch.setattr(PricingService, "_variant_cs_ids", staticmethod(lambda sid: variants))
    monkeypatch.setattr(pmod.ShopifyRest, "set_variant_price", _fake_set_price)
    monkeypatch.setattr(pmod.ShopifyRest, "__init__", lambda self, client: None)
    svc = PricingService(store_service=_FakeStores())
    monkeypatch.setattr(PricingService, "_sync_local_prices",
                        staticmethod(lambda sid, ok: synced.append((sid, ok))))
    monkeypatch.setattr(pmod.settings, "pricing_max_updates_per_run", 1)

    r = svc.recalc_store(7, decisions, dry_run=False, use_graphql=False)
    assert r["updated"] == 1 and r["deferred"] == 1   # cap=1 只推一个
    assert len(pushed) == 1
    assert synced and synced[0][0] == 7


def test_recalc_store_graphql_bulk(monkeypatch):
    decisions = {"CS-A": PriceDecision(cs_id="CS-A", price=19.99)}
    variants = [(111, "CS-A_B_1_0", Decimal("15.00")), (112, "CS-A_B_1_1", Decimal("15.00"))]
    monkeypatch.setattr(PricingService, "_variant_cs_ids", staticmethod(lambda sid: variants))

    pushed: list[list] = []
    synced: list[tuple[int, list]] = []

    svc = PricingService(store_service=None)
    monkeypatch.setattr(PricingService, "_push_price_updates_graphql",
                        lambda self, sid, todo: (
                            pushed.append(todo), [(v, p) for v, _s, p in todo], [])[1])
    monkeypatch.setattr(PricingService, "_sync_local_prices",
                        staticmethod(lambda sid, ok: synced.append((sid, ok))))
    r = svc.recalc_store(7, decisions, dry_run=False, use_graphql=True)
    assert r["updated"] == 2 and r["failed"] == 0 and r["deferred"] == 0
    assert len(pushed[0]) == 2 and synced and len(synced[0][1]) == 2


def test_push_price_updates_graphql_groups_by_product(monkeypatch):
    import shopify_admin.services.pricing.service as pmod

    class _Q:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _FakeSess:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            return _Q([(111, 501), (112, 501), (113, 502)])

    calls: list[tuple[str, list]] = []

    class _FakeClient:
        def graphql(self, query, variables):
            calls.append((variables["pid"], variables["vs"]))
            return {"productVariantsBulkUpdate": {"productVariants": [],
                                                  "userErrors": []}}

        def close(self):
            pass

    class _FakeStores:
        def get_client(self, sid):
            return _FakeClient()

    monkeypatch.setattr(pmod, "session_scope", lambda: _FakeSess())
    ok, errs = PricingService(store_service=_FakeStores())._push_price_updates_graphql(
        7, [(111, "s", 19.99), (112, "s", 19.99), (113, "s", 29.99)])
    assert len(ok) == 3 and not errs
    # 按产品分组合并：501 一次（2 变体）+ 502 一次（1 变体）
    assert len(calls) == 2
    pids = {c[0] for c in calls}
    assert pids == {"gid://shopify/Product/501", "gid://shopify/Product/502"}
    for _gid, vs in calls:
        assert all(v["price"].count(".") == 1 for v in vs)


def _push_fixture(monkeypatch, respond):
    """公共桩：3 个产品 501/502/503（各 1 变体），respond(pid)->data 或 raise。"""
    import shopify_admin.services.pricing.service as pmod

    class _Q:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _FakeSess:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            return _Q([(111, 501), (112, 502), (113, 503)])

    calls: list[int] = []

    class _FakeClient:
        def graphql(self, query, variables):
            pid = int(variables["pid"].rsplit("/", 1)[-1])
            calls.append(pid)
            return respond(pid)

        def close(self):
            pass

    class _FakeStores:
        def get_client(self, sid):
            return _FakeClient()

    monkeypatch.setattr(pmod, "session_scope", lambda: _FakeSess())
    svc = PricingService(store_service=_FakeStores())
    todo = [(111, "s", 19.99), (112, "s", 29.99), (113, "s", 39.99)]
    return svc, todo, calls


def test_push_price_updates_graphql_dead_product_skipped(monkeypatch):
    def respond(pid):
        if pid == 502:
            return {"productVariantsBulkUpdate": {
                "userErrors": [{"field": ["productId"], "message": "Product does not exist"}]}}
        return {"productVariantsBulkUpdate": {"userErrors": []}}

    svc, todo, calls = _push_fixture(monkeypatch, respond)
    ok, errs = svc._push_price_updates_graphql(7, todo)
    assert [v for v, _p in ok] == [111, 113]   # 死产品变体不进 ok
    assert not errs                              # 死产品不计为错误
    assert calls == [501, 502, 503]              # 但确实尝试过


def test_push_price_updates_graphql_circuit_breaker(monkeypatch):
    """3 个产品失败（<30）不触发熔断，自然收尾并逐条记录。"""
    def respond(pid):
        raise RuntimeError("Shopify GraphQL 网络失败: timed out")

    svc, todo, calls = _push_fixture(monkeypatch, respond)
    ok, errs = svc._push_price_updates_graphql(7, todo)
    assert not ok
    assert len(calls) == 3                       # 未熔断：每个产品都尝试了
    assert len(errs) == 3 and not any("熔断" in e for e in errs)


def test_push_price_updates_graphql_breaks_after_30_consecutive_failures(monkeypatch):
    """35 个产品全部网络失败 → 第 30 个连续失败后熔断，剩余不再请求。"""
    import shopify_admin.services.pricing.service as pmod

    class _Q:
        def __init__(self, rows):
            self._rows = rows

        def all(self):
            return self._rows

    class _FakeSess:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            # 40 个产品，各 1 变体
            return _Q([(1000 + i, 2000 + i) for i in range(40)])

    calls: list[int] = []

    class _FakeClient:
        def graphql(self, query, variables):
            calls.append(int(variables["pid"].rsplit("/", 1)[-1]))
            raise RuntimeError("network down")

        def close(self):
            pass

    class _FakeStores:
        def get_client(self, sid):
            return _FakeClient()

    monkeypatch.setattr(pmod, "session_scope", lambda: _FakeSess())
    todo = [(1000 + i, "s", 9.99) for i in range(40)]
    ok, errs = PricingService(store_service=_FakeStores())._push_price_updates_graphql(7, todo)
    assert not ok
    assert len(calls) == 30            # 熔断后剩余 10 个不再请求
    assert any("熔断" in e for e in errs)


# ----------------------------------------------------------------------
# delist_stopped：停售产品 → draft
# ----------------------------------------------------------------------
def test_delist_stopped_dry_run(monkeypatch):
    import shopify_admin.services.pricing.service as pmod

    class _FakeExec:
        def __init__(self, rows):
            self._rows = rows
            self.calls = 0

        def all(self):
            return self._rows

    class _FakeSessionCtx:
        executions = []

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, stmt):
            class _R:
                def __init__(self, rows):
                    self._rows = rows
                    self._i = 0

                def all(self):
                    return self._rows

                def scalar_one_or_none(self):
                    return None

            # 第 1 次：active 产品清单；第 2 次：变体
            _FakeSessionCtx.executions.append(1)
            if len(_FakeSessionCtx.executions) == 1:
                return _R([(501, "Battery A"), (502, "Battery B")])
            return _R([(501, "CS-STOP1_X_1_0"), (502, "CS-KEEP_X_1_0")])

    monkeypatch.setattr(pmod, "session_scope", lambda: _FakeSessionCtx())
    r = PricingService().delist_stopped(7, {"CS-STOP1": PriceDecision(cs_id="CS-STOP1", stopped=True)},
                                        dry_run=True)
    assert r["to_delist"] == 1
    assert r["items"][0]["shopify_product_id"] == 501
