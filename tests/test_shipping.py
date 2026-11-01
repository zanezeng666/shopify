# -*- coding: utf-8 -*-
"""运费同步：CS 费率查表 ×markup + Shopify 回调组装 + 回调端点（全部离线 stub）。"""
import base64
import hashlib
import hmac
import json
from types import SimpleNamespace

import shopify_admin.services.shipping.service as ship_mod
from shopify_admin.services.shipping import ShippingRateService

SECRET = "shpss_abc123"


class _StubSvc(ShippingRateService):
    """离线查表桩：usps($10 基数) + cs_usps($15 基数)，zone 由前缀映射。"""

    def _zone(self, zp):
        return {"900": 8, "100": 3}.get(zp)

    def _carriers(self, origin, dest):
        return [{"carrier": "usps", "name": "USPS"},
                {"carrier": "cs_usps", "name": "CS - USPS"}]

    def _price(self, carrier_code, weight_g, zone):
        return {"usps": 10.0, "cs_usps": 15.0}[carrier_code]

    def _unit_weight(self, cs_id):
        return {"CS-TST": 270}.get(cs_id, 0)


# ----------------------------------------------------------------------
# 报价：基数 ×1.2 / 邮编分区 / 超重尾档兜底
# ----------------------------------------------------------------------
def test_quote_weight_markup(monkeypatch):
    monkeypatch.setattr(ship_mod.settings, "shipping_markup", 1.2)
    q = _StubSvc().quote_weight(540, "90001")        # zone 8, 2×270g
    assert q["zone"] == 8 and q["zip_prefix"] == "900"
    usps = next(c for c in q["carriers"] if c["carrier"] == "usps")
    assert usps["base_price"] == 10.0 and usps["price"] == 12.0   # ×1.2
    assert q["carriers"][0]["carrier"] == "usps"                 # 按展示价升序


def test_quote_weight_zone_miss(monkeypatch):
    q = _StubSvc().quote_weight(540, "99999")
    assert "error" in q


def test_price_over_weight_falls_to_max_tier(monkeypatch):
    """总重超表尾：第一查（向上取档）无果 → 尾档兜底价。"""

    class _Conn:
        calls = 0

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=None):
            _Conn.calls += 1
            return _Q(12.5 if _Conn.calls >= 2 else None)

    class _Q:
        def __init__(self, val):
            self._val = val

        def first(self):
            return (self._val,) if self._val is not None else None

    monkeypatch.setattr(ship_mod, "get_cs_engine", lambda: SimpleNamespace(connect=_Conn))
    p = ShippingRateService()._price("usps", 99999, 8)
    assert p == 12.5


# ----------------------------------------------------------------------
# 回调组装：grams 优先 / SKU 回退查库 / 非美国空 rates / 分单位
# ----------------------------------------------------------------------
def test_shopify_rates_cents_and_country(monkeypatch):
    monkeypatch.setattr(ship_mod.settings, "shipping_markup", 1.2)
    svc = _StubSvc()
    items = [{"sku": "CS-TST_Acme_47_0", "quantity": 2, "grams": 270}]
    rates = svc.shopify_rates(items, {"country": "US", "postal_code": "90001"})
    assert [r["service_code"] for r in rates] == ["usps", "cs_usps"]
    assert rates[0]["total_price"] == "1200"          # 12.00 USD → 分
    assert rates[0]["currency"] == "USD"
    # 非美国目的地 → 无报价
    assert svc.shopify_rates(items, {"country": "CA", "postal_code": "M5V"}) == []


def test_cart_weight_sku_fallback(monkeypatch):
    svc = _StubSvc()
    # grams 缺失 → SKU 解析 cs_id → _unit_weight 回退
    w = svc._cart_weight_g([{"sku": "CS-TST_Acme_47_0", "quantity": 2},
                            {"sku": "NOT-CS", "quantity": 5, "grams": 100}])
    assert w == 270 * 2 + 100 * 5


# ----------------------------------------------------------------------
# 回调端点：HMAC 验签 / payload 解析 / 未登记店铺放行
# ----------------------------------------------------------------------
def _mk_app(monkeypatch, quote_result):
    monkeypatch.setattr("shopify_admin.api.routers.shipping._svc", _StubSvc())
    monkeypatch.setattr("shopify_admin.api.routers.shipping._stores",
                        type("S", (), {"find_credentials_by_domain":
                               staticmethod(lambda d: None)})())
    from fastapi.testclient import TestClient
    from shopify_admin.api.app import create_app
    return TestClient(create_app())


_PAYLOAD = {"rate": {"items": [{"sku": "CS-TST_Acme_47_0", "quantity": 1, "grams": 270}],
                     "destination": {"country": "US", "postal_code": "90001"}}}


def test_callback_ok(monkeypatch):
    c = _mk_app(monkeypatch, None)
    rsp = c.post("/shopify/callback/carrier-rates", json=_PAYLOAD,
                 headers={"X-Shopify-Shop-Domain": "any.myshopify.com"})
    assert rsp.status_code == 200
    rates = rsp.json()["rates"]
    assert rates[0]["service_code"] == "usps" and rates[0]["total_price"] == "1200"


def test_callback_hmac_reject(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        "shopify_admin.api.routers.shipping._stores",
        SimpleNamespace(find_credentials_by_domain=lambda d: SimpleNamespace(
            api_secret=SECRET, api_key="k", domain="b.myshopify.com")))

    from fastapi.testclient import TestClient
    from shopify_admin.api.app import create_app
    c = TestClient(create_app())

    raw = json.dumps(_PAYLOAD).encode()
    bad = c.post("/shopify/callback/carrier-rates", content=raw, headers={
        "X-Shopify-Shop-Domain": "b.myshopify.com",
        "X-Shopify-Hmac-Sha256": "deadbeef",
    })
    assert bad.status_code == 401

    good_sig = base64.b64encode(
        hmac.new(SECRET.encode(), raw, hashlib.sha256).digest()).decode()
    ok = c.post("/shopify/callback/carrier-rates", content=raw, headers={
        "X-Shopify-Shop-Domain": "b.myshopify.com",
        "X-Shopify-Hmac-Sha256": good_sig,
    })
    assert ok.status_code == 200 and ok.json()["rates"]
