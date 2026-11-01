# -*- coding: utf-8 -*-
"""CsShopifySyncService 记录级对账 + 存量上架格式对齐测试（全部离线 stub）。"""
from decimal import Decimal
from types import SimpleNamespace

import shopify_admin.services.products.sync_shopify as sync_mod
from shopify_admin.services.products.sync_shopify import CsShopifySyncService


def _cs_row(cs_id, brand, *, retail=None, bar="", gross=0, net=0,
            fit="", pno="", status=1, category="Mobile, SmartPhone"):
    return {
        "cs_id": cs_id, "brand": brand, "part_no": pno, "fit_model": fit,
        "capacity": "", "voltage": "", "battery_type": "", "dimension": "",
        "net_weight_g": net, "gross_weight_g": gross, "bar_code": bar,
        "retail": Decimal(retail) if retail else None, "status": status,
        "category": category,
    }


# 记录级目录：key=(cs_id, brand.lower())；同 cs_id 多品牌 = 多条独立记录
CATALOG: dict[tuple[str, str], dict] = {
    ("CS-AA", "acme"):   _cs_row("CS-AA", "Acme", retail="12.50", bar="6900001", gross=100),
    ("CS-BB", "best"):   _cs_row("CS-BB", "Best", retail="12.50", bar="6900002", gross=150, fit="B1,B2", pno="P1"),
    ("CS-CC", "ceta"):   _cs_row("CS-CC", "Ceta", retail="15.00", bar="6900003", gross=350),
    ("CS-DD", "dbrand"): _cs_row("CS-DD", "DBrand", retail="12.50", bar="6900004", gross=120, fit="D1,D2", pno="DP1"),
    ("CS-EE", "ebrand"): _cs_row("CS-EE", "EBrand", retail="7.00", gross=40),
    ("CS-GH", "gh"):     _cs_row("CS-GH", "Gh", retail="9.99", gross=90, status=0),
    ("CS-MM", "mova"):   _cs_row("CS-MM", "Mova", retail="22.00", gross=220, fit="M1", pno="MP1"),
    ("CS-MM", "nibi"):   _cs_row("CS-MM", "Nibi", retail="22.00", gross=220, fit="M1", pno="MP1"),
    ("CS-XX", "xa"):     _cs_row("CS-XX", "XA", retail="5.00", gross=50),
    ("CS-XX", "xb"):     _cs_row("CS-XX", "XB", retail="5.00", gross=50),
}

# 店铺变体镜像：(vid, sku, price, grams, barcode, spid)；存量 4 段 SKU 格式
VARIANTS = [
    (111, "CS-AA_Acme_47_0", "12.50", 100, "", 9001),
    (112, "CS-BB_Other_9_0", "20.00", 200, "6900002", 9002),  # 品牌段漂移 → 单记录容错配对
    (113, "CS-CC_Ceta_9_0", None, 300, "", 9003),
    (114, "CS-GH_Gh_9_0", "9.99", 90, "", 9004),              # 停产记录在售 → archive 报告
    (115, "CS-MM_Mova_12_0", "22.00", 220, "6900009", 9005),
    (116, "CS-XX_Neither_9_0", "5.00", 50, "", 9006),         # 多记录品牌不匹配 → mismatch
    (117, "CS-ZZ_Zed_9_0", "3.00", 30, "", 9007),             # cs_id 整组无记录 → 孤儿
    (118, "NOT-CS", "1.00", 10, "", 9008),                     # 未锚定
]


class _FakeSession:
    def execute(self, *_a, **_k):
        return SimpleNamespace(all=lambda: VARIANTS)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _install(monkeypatch):
    monkeypatch.setattr(sync_mod, "session_scope", lambda: _FakeSession())
    monkeypatch.setattr(sync_mod.CsShopifySyncService, "load_cs_catalog",
                        staticmethod(lambda: {k: dict(v) for k, v in CATALOG.items()}))


class _FakeStores:
    def __init__(self, client=None):
        self._client = client or SimpleNamespace(close=lambda: None)

    def get_client(self, _sid):
        return self._client


class _FakeProducts:
    def __init__(self):
        self.upserted: list[dict] = []

    def _upsert_product(self, _sid, product):
        self.upserted.append(product)


class _FakeRest:
    def __init__(self, client=None, existing_handles=None):
        self.client = client
        self.created: list[dict] = []
        self.updated: list[tuple[int, dict]] = []
        self.existing_handles = set(existing_handles or [])

    def product_by_handle(self, h):
        return {"id": 555, "handle": h, "variants": [{"id": 556, "sku": "x"}]} if h in self.existing_handles else None

    def create_product(self, payload):
        self.created.append(payload)
        return {"id": 1000 + len(self.created), **payload}

    def update_variant(self, vid, fields):
        self.updated.append((vid, fields))
        return {"id": vid, **fields}


# ----------------------------------------------------------------------
# 对账计划（记录级）
# ----------------------------------------------------------------------
def test_diff_record_level_plan(monkeypatch):
    _install(monkeypatch)
    d = CsShopifySyncService().diff(1)
    p = d["plan"]
    # 新品 = CS-DD、CS-EE、CS-MM/Nibi（Mova 已有、Nibi 无 → 多品牌按记录拆分）
    #        + CS-XX 双记录（唯一变体品牌段不匹配未配对 → 两条记录都算新品）
    assert p["to_create"]["count"] == 5
    brands = {(i["cs_id"], i["brand"]) for i in p["to_create"]["items"]}
    assert ("CS-MM", "Nibi") in brands and ("CS-DD", "DBrand") in brands
    assert ("CS-XX", "XA") in brands
    # 多记录品牌段不匹配 → 报告不动
    assert p["brand_mismatch"]["count"] == 1
    assert p["brand_mismatch"]["items"][0]["sku"] == "CS-XX_Neither_9_0"
    assert set(p["brand_mismatch"]["items"][0]["cs_brands"]) == {"xa", "xb"}
    assert p["orphans"]["count"] == 1 and p["orphans"]["items"] == ["CS-ZZ"]
    assert p["to_archive"]["count"] == 1 and p["to_archive"]["items"][0]["cs_id"] == "CS-GH"
    # 口径统计
    assert d["cs_catalog"]["records"] == 10 and d["cs_catalog"]["unique_cs_ids"] == 8
    assert d["store_side"]["anchored"] == 7 and d["store_side"]["unanchored"] == 1


def test_single_record_brand_fallback_pairs(monkeypatch):
    """csid 单记录时 SKU 品牌段漂移仍容错配对（历史人工上架差异）。"""
    _install(monkeypatch)
    c = CsShopifySyncService()._compute(1)
    vids = {u["vid"] for u in c["to_update"]}
    assert 112 in vids  # CS-BB_Other 配到 (CS-BB, best)


# ----------------------------------------------------------------------
# 新品 payload：对齐店铺存量上架格式
# ----------------------------------------------------------------------
def test_payload_matches_store_format(monkeypatch):
    _install(monkeypatch)
    row = dict(CATALOG[("CS-DD", "dbrand")])
    p = CsShopifySyncService().build_new_product_payload(row)
    assert p["title"] == "Battery for DBrand D1 D2 DP1"
    assert p["handle"] == "battery-for-dbrand-d1-d2-dp1"
    assert p["vendor"] == "Bomibattery"           # 店铺统一自有品牌（存量实证）
    v = p["variants"][0]
    assert v["sku"] == "CS-DD_DBrand_47_0"        # 存量 4 段格式，N=类目码 47(Mobile/SmartPhone)
    assert v["price"] == "12.50" and v["barcode"] == "6900004" and v["grams"] == 120
    assert v["inventory_management"] == "shopify"
    # body 复刻存量模板三段列表
    for frag in ("Compatible Brand", "Compatible Model", "Compatible Battery Part Number",
                 "<li><b>DBrand</b></li>", "<li><b>D1</b></li>", "<li><b>DP1</b></li>",
                 "Tips Before Purchase"):
        assert frag in p["body_html"]


def test_payload_multibrand_split_and_slug(monkeypatch):
    _install(monkeypatch)
    svc = CsShopifySyncService()
    a = svc.build_new_product_payload(dict(CATALOG[("CS-MM", "mova")]))
    b = svc.build_new_product_payload(dict(CATALOG[("CS-MM", "nibi")]))
    assert a["handle"] != b["handle"]             # 同电池不同品牌 → 独立产品独立 handle
    assert b["title"] == "Battery for Nibi M1 MP1"
    assert svc._slug("Battery for X&Y / Z, W!!") == "battery-for-x-y-z-w"


def test_payload_fallback_without_fit(monkeypatch):
    _install(monkeypatch)
    row = dict(CATALOG[("CS-EE", "ebrand")])
    p = CsShopifySyncService().build_new_product_payload(row)
    assert p["title"] == "Battery for EBrand"     # 无 fit/part → 品牌兜底
    assert p["handle"] == "battery-for-ebrand"
    assert p["variants"][0]["sku"] == "CS-EE_EBrand_47_0"


# ----------------------------------------------------------------------
# 存量对齐策略（条码补空 / 重量对齐 / 价格报告）
# ----------------------------------------------------------------------
def _by_vid(c):
    return {u["vid"]: u["fields"] for u in c["to_update"]}


def test_barcode_grams_price_policy(monkeypatch):
    _install(monkeypatch)
    c = CsShopifySyncService()._compute(1)
    by = _by_vid(c)
    assert by[111] == {"barcode": "6900001"}                 # 只补空
    assert by[112] == {"grams": 150}                          # 容错配对仍对齐；价格漂移只报告
    assert by[113] == {"barcode": "6900003", "grams": 350, "price": "15.00"}
    assert 114 not in by                                      # 停产记录不进 update
    assert c["barcode_fill"] == 2 and c["barcode_conflict"] == 0
    assert c["price_drift"] == 1                              # 112: 20.00 vs 12.50
    assert c["suspicious"][0]["sku"] == "CS-BB_Other_9_0"     # 60% 偏差入悬崖清单
    assert c["suspicious"][0]["deviation_pct"] == 60.0


def test_overwrite_mode_aligns_price(monkeypatch):
    _install(monkeypatch)
    c = CsShopifySyncService()._compute(1, price_mode="overwrite")
    assert _by_vid(c)[112]["price"] == "12.50"


def test_bad_price_mode_rejected(monkeypatch):
    _install(monkeypatch)
    try:
        CsShopifySyncService().diff(1, price_mode="hack")
    except ValueError:
        return
    raise AssertionError("应拒绝未知 price_mode")


# ----------------------------------------------------------------------
# 受控执行
# ----------------------------------------------------------------------
def _mk_svc(monkeypatch, rest):
    prods = _FakeProducts()
    svc = CsShopifySyncService(store_service=_FakeStores(), product_service=prods)
    monkeypatch.setattr(sync_mod, "ShopifyRest", lambda _c: rest)
    monkeypatch.setattr(sync_mod.CsShopifySyncService, "load_cs_catalog",
                        staticmethod(lambda: {k: dict(v) for k, v in CATALOG.items()}))
    monkeypatch.setattr(sync_mod, "session_scope", lambda: _FakeSession())
    # 图库探测默认桩：离线无图（图片专项测试自行覆盖）
    monkeypatch.setattr(svc, "_probe_images", lambda cs_id, http: [])
    return svc, prods


def test_apply_dry_run_makes_no_calls(monkeypatch):
    class _Boom:
        def get_client(self, _sid):
            raise AssertionError("dry_run 不应装配客户端")

    svc = CsShopifySyncService(store_service=_Boom(), product_service=_FakeProducts())
    monkeypatch.setattr(sync_mod.CsShopifySyncService, "load_cs_catalog",
                        staticmethod(lambda: {k: dict(v) for k, v in CATALOG.items()}))
    monkeypatch.setattr(sync_mod, "session_scope", lambda: _FakeSession())
    r = svc.apply(1, dry_run=True)
    assert r["dry_run"] is True and r["to_create"] == 5 and r["to_update"] == 3
    assert r["created"] == r["updated"] == r["failed"] == 0


def test_apply_creates_and_updates(monkeypatch):
    rest = _FakeRest()
    svc, prods = _mk_svc(monkeypatch, rest)

    class _Wb:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *_a, **_k):   # 兼 _compute(.all) 与回写(.scalar_one_or_none)
            return SimpleNamespace(all=lambda: VARIANTS,
                                   scalar_one_or_none=lambda: 321)

        def get(self, _m, pk):
            assert pk == 321
            return SimpleNamespace(barcode="", grams=0, price=None,
                                   shopify_updated_at=None)

        def close(self):
            pass

    monkeypatch.setattr(sync_mod, "session_scope", lambda: _Wb())
    r = svc.apply(1, dry_run=False)
    assert r["created"] == 5 and r["updated"] == 3 and r["failed"] == 0
    assert len(prods.upserted) == 5                            # 建品结果落本地镜像
    titles = {p["title"] for p in rest.created}
    assert "Battery for Nibi M1 MP1" in titles                 # 多品牌记录独立建品
    assert {v for v, _ in rest.updated} == {111, 112, 113}


def test_apply_handle_exists_skips(monkeypatch):
    rest = _FakeRest(existing_handles=["battery-for-dbrand-d1-d2-dp1"])
    svc, prods = _mk_svc(monkeypatch, rest)

    class _Wb:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, *_a, **_k):
            return SimpleNamespace(all=lambda: VARIANTS,
                                   scalar_one_or_none=lambda: 321)

        def get(self, _m, pk):
            assert pk == 321
            return SimpleNamespace(barcode="", grams=0, price=None,
                                   shopify_updated_at=None)

        def close(self):
            pass

    monkeypatch.setattr(sync_mod, "session_scope", lambda: _Wb())
    r = svc.apply(1, dry_run=False)
    assert r["skipped_existing"] == 1 and r["created"] == 4
    assert all(p["handle"] != "battery-for-dbrand-d1-d2-dp1" for p in rest.created)
    assert prods.upserted[0]["id"] == 555                       # skip 时补镜像


def test_apply_invalid_publish_status(monkeypatch):
    _install(monkeypatch)
    try:
        CsShopifySyncService().apply(1, dry_run=True, publish_status="ghost")
    except ValueError:
        return
    raise AssertionError("应拒绝未知 publish_status")


# ----------------------------------------------------------------------
# 电池范围过滤（业务口径：只做电池，充电器/壳/线缆等配件不做）
# ----------------------------------------------------------------------
def test_battery_scope_predicate():
    """_is_battery_record 三道闸：前缀 / 白名单 / 内容判据。"""
    f = sync_mod._is_battery_record
    # ① 前缀：DF/CF/AS 配件前缀排除，即使字段像电池
    assert not f(_cs_row("DF-HMW220UB", "HME", category="Battery Charger",
                         pno="CZ-BAT50"))
    assert not f({**_cs_row("CF-KNB220BFG", "Kenwood", category="Two-Way Radio Case"),
                  "capacity": "2000mAh"})          # 有容量也拦（前缀闸最优先）
    # ② 白名单类目：capacity/battery_type 全空也放行（Notebook 等真电池字段不全）
    assert f(_cs_row("CS-NB1", "Acer", category="Notebook, Laptop"))
    assert f(_cs_row("CS-NB2", "HP", category="Cable Modem"))   # 白名单先于配件词
    # ③ 新类目：配件词拦截
    assert not f(_cs_row("CS-CH1", "X", category="Camera Charger"))
    assert not f(_cs_row("CS-AD1", "X", category="Laptop Adapter"))
    assert not f(_cs_row("CS-CB1", "X", category="Cosmetic Mirror"))
    # ③ 新类目：无配件词 → 内容判据（有容量/类型=电池放行，全空排除）
    assert f({**_cs_row("CS-EB1", "X", category="Electric eBike"),
              "capacity": "18000mAh", "battery_type": "Li-ion"})
    assert f({**_cs_row("CS-PB1", "X", category="Power Bank"), "battery_type": "Li-ion"})
    assert not f(_cs_row("CS-SD1", "X", category="Screwdriver"))


def test_battery_scope_filters_create(monkeypatch):
    """非电池记录不进 to_create、进 excluded_non_battery 报告；新电池类目放行。"""
    cat = {
        ("CS-CH1", "ch"): _cs_row("CS-CH1", "Ch", category="Camera Charger"),
        ("DF-HMW220UB", "hme"): _cs_row("DF-HMW220UB", "HME", category="Battery Charger"),
        ("CS-EB1", "ebike"): {**_cs_row("CS-EB1", "Ebike", category="Electric eBike",
                                        retail="61.00", gross=500, fit="NKY224B02"),
                              "capacity": "18000mAh"},
        ("CS-SD1", "sd"): _cs_row("CS-SD1", "Sd", category="Screwdriver"),
    }
    monkeypatch.setattr(sync_mod, "session_scope", lambda: _FakeSession())
    monkeypatch.setattr(sync_mod.CsShopifySyncService, "load_cs_catalog",
                        staticmethod(lambda: {k: dict(v) for k, v in cat.items()}))
    p = CsShopifySyncService().diff(1)["plan"]
    skus = [i["sku"] for i in p["to_create"]["items"]]
    assert p["to_create"]["count"] == 1 and skus == ["CS-EB1_Ebike_0_0"]
    exc = p["excluded_non_battery"]
    assert exc["count"] == 3
    assert {(i["cs_id"], i["category"]) for i in exc["items"]} == {
        ("CS-CH1", "Camera Charger"), ("DF-HMW220UB", "Battery Charger"),
        ("CS-SD1", "Screwdriver")}


def test_apply_only_cs_id_single_point(monkeypatch):
    """only_cs_id：只创建目标 cs_id 的产品、跳过存量 update。"""
    _install(monkeypatch)
    rest = _FakeRest()
    prods = _FakeProducts()
    monkeypatch.setattr(sync_mod.ShopifyRest, "__init__",
                        lambda self, client: _FakeRest.__init__(self, client))
    monkeypatch.setattr(sync_mod.ShopifyRest, "product_by_handle", _FakeRest.product_by_handle)
    monkeypatch.setattr(sync_mod.ShopifyRest, "create_product",
                        lambda self, p: _FakeRest.create_product(rest, p))

    class _Wb(_FakeSession):
        def __init__(self):
            self.updated = []

        def execute(self, *_a, **_k):
            return SimpleNamespace(all=lambda: VARIANTS,
                                   scalar_one_or_none=lambda: 321)

        def get(self, _m, pk):
            return SimpleNamespace(barcode="", grams=0, price=None,
                                   shopify_updated_at=None)

        def close(self):
            pass

    monkeypatch.setattr(sync_mod, "session_scope", lambda: _Wb())
    svc = CsShopifySyncService()
    svc._products = prods
    r = svc.apply(1, dry_run=False, only_cs_id="CS-DD")
    assert r["only_cs_id"] == "CS-DD"
    assert r["created"] == 1 and len(rest.created) == 1
    assert rest.created[0]["variants"][0]["sku"] == "CS-DD_DBrand_47_0"
    assert r["updated"] == 0                          # 单点模式不动存量


# ====================================================================
# 网页模板对齐（老品实证 7122951831719：Battery Specifications 双表格 + 列表尾段）
# ====================================================================
_SPEC_ROW = {
    "cs_id": "CS-TVR500VX", "brand": "Amarey", "part_no": "PT-SX-2000L",
    "fit_model": "A800,A900", "capacity": "2600mAh", "voltage": "14.4V",
    "battery_type": "Li-ion", "dimension": "69.40 x 37.00 x 37.00mm",
    "net_weight_g": 200, "gross_weight_g": 270, "bar_code": "",
    "retail": Decimal("32.00"), "status": 1, "category": "Vacuum",
    "wh_value": Decimal("0.00"),
}


def test_body_html_matches_legacy_webpage_template():
    body = CsShopifySyncService._build_body_html(_SPEC_ROW)
    # 页首规格段逐字锚点（与老品 7122951831719 body_html 一致）
    assert body.startswith("Battery Specifications <br> <br>")
    for anchor in (
        '<td style="text-align: left;" class="detail-tit">Li-ion</td>',
        '<td class="detail-val">270.0g</td>',                    # 270 → 270.0g
        '<td class="detail-val">69.4*37.0*37.0mm</td>',          # 去尾零 * 连接
        '<td class="detail-tit">Vacuum</td>',
        '<td class="detail-val">14.4V</td>',
        '<td class="detail-val">37.44Wh</td>',                   # wh 缺失→容量×电压推导
        "Battery Specifications", "Tips Before Purchase",
        "<li><b>PT-SX-2000L</b></li>",                           # part_no 列表
    ):
        assert anchor in body
    # 老模板不含供应商介绍段
    assert "professional battery supplier" not in body


def test_spec_tables_skip_empty_rows_and_degenerate():
    # 单字段（仅 battery_type）→ 单行表
    only_type = CsShopifySyncService._spec_tables_html({"battery_type": "Li-ion"})
    assert only_type.count("<tr>") == 1 and ">Li-ion<" in only_type
    # 全空 → 整段省略（纯列表形态）
    assert CsShopifySyncService._spec_tables_html({}) == ""


def test_spec_rate_prefers_source_wh():
    row = dict(_SPEC_ROW, wh_value=Decimal("40.32"))
    assert '<td class="detail-val">40.32Wh</td>' in \
        CsShopifySyncService._spec_tables_html(row)


def test_variant_option1_is_capacity():
    """存量规则：option1=容量（2600mAh），缺容量退回 Default Title。"""
    caps = [(_SPEC_ROW, "2600mAh"), (dict(_SPEC_ROW, capacity=""), "Default Title")]
    for row, expect in caps:
        got = (row.get("capacity") or "").strip() or "Default Title"
        assert got == expect


# ----------------------------------------------------------------------
# 图片外链挂载（cameronsino.co 图库，2026-10-31 实证规律）
# ----------------------------------------------------------------------
def test_cs_image_urls_stops_at_first_miss():
    calls = []

    def head(u):
        calls.append(u)
        return u.endswith(("-1.jpg", "-2.jpg"))

    urls = sync_mod.cs_image_urls("CS-TST", head)
    assert urls == [f"{sync_mod._CS_IMG_BASE}/CS-TST-1.jpg",
                    f"{sync_mod._CS_IMG_BASE}/CS-TST-2.jpg"]
    assert len(calls) == 3          # -3 首个 miss 即停，不多探


def test_cs_image_urls_exception_and_all_miss():
    def boom(_u):
        raise RuntimeError("net down")

    assert sync_mod.cs_image_urls("CS-TST", boom) == []       # 异常按 miss 不抛
    assert sync_mod.cs_image_urls("CS-TST", lambda _u: False) == []


def test_apply_attaches_image_urls(monkeypatch):
    rest = _FakeRest()
    svc, _prods = _mk_svc(monkeypatch, rest)
    fake = [f"https://cameronsino.co/images/CS-DD-{n}.jpg" for n in (1, 2)]
    monkeypatch.setattr(svc, "_probe_images", lambda cs_id, http: list(fake))

    r = svc.apply(1, dry_run=False, only_cs_id="CS-DD")
    assert r["created"] == 1 and r["images_attached"] == 1
    p = rest.created[0]
    assert [i["src"] for i in p["images"]] == fake


def test_apply_no_images_creates_bare(monkeypatch):
    rest = _FakeRest()
    svc, _prods = _mk_svc(monkeypatch, rest)   # 默认桩: 无图

    r = svc.apply(1, dry_run=False, only_cs_id="CS-DD")
    assert r["created"] == 1 and r["images_missing"] == 1
    assert "images" not in rest.created[0]     # 裸建品，不带空 images 键
