# -*- coding: utf-8 -*-
"""CS 产品库 → Shopify 产品同步引擎（对账 + 分级执行）。

数据链路：
    cs_new.cs_product（bmai 维护，权威产品主数据；粒度 = 记录级 (cs_id, brand)：
      同一颗电池按适配品牌是独立 CS 产品记录 —— 实证 22143 行 / distinct cs_id 14691，
      其中 7452 行为多品牌记录；店铺 4112 个多品牌 cs_id 全部"每品牌一个独立产品"，
      忠实映射 CS 源头记录粒度，而非店铺自行拆分）
      └─ (cs_id, brand) ──SKU 解析 CS-{csid}_{Brand}_{N}_{M}──> product_variants（镜像）
                                                        └─ shopify_variant_id → Shopify 店铺

一致性策略（2026-10-31 全量实证）：
- 匹配键    记录级 (cs_id, brand.lower())：SKU 品牌段 vs CS 记录 brand 对齐率 93.6%；
            cs_id 仅 1 条记录时容错配对（历史人工上架品牌段差异，如 _T-Mobile vs CS 记录 HTC）；
            多记录品牌段不匹配 → brand_mismatch 报告（不动店铺数据）
- 价格      实证 99.8% 变体价格 ≠ CS 建议零售价 → 店铺为独立零售定价体系，默认 report-only；
            price_mode="overwrite" 才强制对齐；店铺缺价变体两模式均补零售价；新品首发价=零售价
- 重量      实证漂移 0（历史同源）→ 自动对齐（毛重优先，净重兜底）
- 条码      实证漂移全为"补齐型"（店铺空·CS 有）、冲突 0 → 只补空、冲突跳过计数
- 停产/孤儿 默认只报告不下架（破坏性动作留人工）
- 营销字段  CREATE 时生成且对齐店铺既有上架格式（实证 22k 老品同构）：
              title  = "Battery for {brand} {fit_model...} {part_no...}"
              handle = battery-for-{slug}；vendor = Estry（店铺统一自有品牌）
              body   = 存量复刻模板（Compatible Brand/Model/Part Number 列表）
              SKU    = CS-{csid}_{Brand}_{类目码}_0（存量 23975/23976 为 4 段格式；
                       履约 SkuResolver 正则 ^CS-[A-Z0-9]+ 前缀锚定，段数不敏感）
            UPDATE 永不覆盖营销字段（店铺人工资产）
- 幂等      create 以 handle 查重；update 仅字段 diff 非空才发请求；结果即时回写镜像
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope
from shopify_admin.models.product import ProductVariant
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.products.service import ProductService
from shopify_admin.services.stores.service import StoreService

_CS_ID_RE = re.compile(r"^(CS-[A-Za-z0-9]+)")
_SUSPICIOUS_PCT = 0.5      # 价格跳变阈值：|店铺价-CS零售|/CS零售 > 50% 列入人工复核清单
_STORE_VENDOR = "Estry"   # 店铺自有品牌（2026-11-03 由 Bomibattery 切换为美国品牌
                          #  Estry，域名 estrybattery.com；同步改线上 15k+ 存量 vendor）

# ---- 产品图片外链（cameronsino.co 图库站，2026-10-31 实证） ----
# 规律: https://cameronsino.co/images/CS-{ID}-{N}.jpg，N 从 1 连续递增至首个 404 停；
# 每品 3~9 张不等；抽样 100 个 cs_id 命中 98%；与店铺老品图片数交叉验证完全吻合
# （BTR100MX=5/CNM200SL=4/RTK300MD=3/2HCFX2NR=3，老品当年即从此外链搬图未改名）。
_CS_IMG_BASE = "https://cameronsino.co/images"
_CS_IMG_MAX_N = 12               # 单品图片数封顶（实测最大 9，留余量）
_CS_IMG_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def cs_image_urls(cs_id: str, head, max_n: int = _CS_IMG_MAX_N) -> list[str]:
    """探测 cs_id 在 cameronsino.co 图库的可用图片 URL 列表。

    head: callable(url) -> bool（HTTP 200 与否），注入以便测试；
    编号连续（-1,-2,…），首个 miss 即停；异常按 miss 处理（图片缺失不阻断建品）。
    """
    urls: list[str] = []
    for n in range(1, max_n + 1):
        u = f"{_CS_IMG_BASE}/{cs_id}-{n}.jpg"
        try:
            ok = head(u)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            break
        urls.append(u)
    return urls

# 类目 → 存量 SKU 第 3 段 N（CS 内部类目编码）。
# 键 = cs_product 现行 category 文本（与 load_cs_catalog 读取值同源）；
# 由存量 4 段 SKU join CS 目录按类目取众数重建（scripts/_build_catmap.py）：
# 96 类目、21941/22529 (97%) 一致；<90% 命中的歧义条目行内标注（历史人工上架混用）。
# 未知类目兜底 0（"Alarm System" 的 0 是真实编码）。
_CATEGORY_SKU_CODE: dict[str, int] = {
    "Mobile, SmartPhone": 47, "Notebook, Laptop": 50, "Camera": 9,
    "Cordless Phone": 12, "Power Tools": 55, "Medical": 43,
    "Equipment, Survey, Test": 27, "Vacuum": 77, "Barcode Scanner": 5,
    "Two-Way Radio": 75, "Tablet": 69, "GPS, Navigator": 31,
    "Speaker": 66, "Wireless Headset": 81, "PDA, Pocket PC": 53,
    "Hotspot": 33, "PLC": 54, "CMOS / BackUp": 11, "Dog Collar": 17,
    "Crane Remote Control": 13, "Lawn Mowers": 38,
    "Media Player": 48,   # 79%
    "Payment Terminal": 52, "RAID Controller": 58, "Remote Control": 61,
    "Smartwatch": 65, "Gardening Tools": 30, "Shaver": 63, "BabyPhone": 4,
    "Flashlight": 28, "Game Console": 29, "E-book, E-reader": 22,
    "Emergency Lighting": 26, "Thermal Camera": 70, "DAB Digital": 15,
    "Cable Modem": 7, "Door Lock": 18, "Battery Pack": 14,
    "Home Security Camera": 32, "Battery Grip": 84, "Amplifier": 2,
    "Satellite Phone": 62, "Printer": 56, "Projector": 57,
    "Remote Start and Entry Systems": 338, "Smart Home": 64, "Pager": 51,
    "VoIP Phone": 79,
    "Alarm System": 0,
    "Cars": 59,   # 53%，Drones/Airsoft/RC/FPV/Robot 等共用 59
    "Portable Printer": 56,   # 57%
    "Drones": 59,   # 52%
    "Dashcam": 31,   # 57%，与 GPS(31) 同码
    "Diagnostic Scanner": 132, "Toothbrush": 73, "Personal Care": 118,
    "Automatic Flusher": 3, "Laser": 37, "Storage": 68,
    "Bicycles Flashlights": 40, "Calculator": 8, "Recorder": 60,
    "Car Speaker": 10, "Cash Register": 52,
    "Communication & Conferencing": 106,
    "DVD Player": 15,   # 66%，与 DAB Digital(15) 同码
    "DVB-T": 19, "Electronic Magnifier": 24, "Kitchenware": 36,
    "Mobile Fax": 46, "Time Clock": 72, "VR": 80, "Body Camera": 9,
    "Dictionary": 16, "E-cigarette": 21, "Heated Clothes": 71,
    "LED Light": 39, "Automatic Doors": 18, "Dry Herb Vaporizers": 21,
    "Electronic Tuner": 27, "FPV": 59, "Gimbals": 9,
    "Marine Safety & Flotation Devices": 340, "Microscope": 45,
    "POS Workstation": 131, "Portable Led Desk Lamp": 39, "RC Hobby": 59,
    "Airsoft Guns": 59, "Robot": 59, "Solar Marine Light": 125,
    "Soldering Tools": 55,
    "Stage Monitor System": 127, "Telescope": 339, "Vehicles": 78,
    "Remote Controller": 121,   # 61%，存量 121/61 混用
    "Keyboard,Mouse": 82,   # 44%
}

_CS_COLS = (
    "cs_id, brand, part_no, fit_model, capacity, voltage, battery_type, "
    "dimension, net_weight_g, gross_weight_g, bar_code, "
    "suggested_retail_price, status, category, wh_value"
)

# 配件类目词（小写子串匹配；仅对历史白名单之外的类目生效——
# 白名单里 Cable Modem 含 cable 不受影响）
_NON_BATTERY_KW = ("charger", "adapter", "cable", "coupler", "case",
                   "mirror", "microphone")

# 品类收缩黑名单（2026-11-12 用户拍板）：手机/相机/笔记本三类不再建新品，
# 存量品已批量转 DRAFT（deploy/rebalance_exec.py）；CS category 文本口径。
_EXCLUDED_CATEGORIES = {"Mobile, SmartPhone", "Notebook, Laptop", "Camera"}

# ==================================================================
# 详情页 body v2（2026-11-03）：分区化模板，全部内联样式（Shopify 描述区
# 过滤 script/iframe/外部 CSS，内联 style 安全）；移动端优先（% 宽度）。
# 政策承诺为占位文案——政策确定后改此处，refresh_body.py 全局重刷即可。
# ==================================================================
_POLICY = {
    "warranty": "12-Month Warranty",
    "returns": "30-Day Easy Returns",
    "shipping": "Ships from US in 48h",
    # 认证口径（2026-11-03 与用户核实）：CE/RoHS 未做过，撤下虚假宣称
    # （FTC 风险）；UN38.3 为锂电池运输强制测试（出口必过）、ISO9001 工厂
    # 质量体系认证已取得——只保留真实的
    "certs": "UN38.3 & ISO9001 Certified",
}
_H3_STYLE = ("margin:14px 0 8px;font-size:18px;font-weight:700;color:#1B2A41;"
             "border-bottom:2px solid #1B2A41;padding-bottom:4px;")


def _esc(x: Any) -> str:
    return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _h3(title: str) -> str:
    return f'<h3 style="{_H3_STYLE}">{title}</h3>'


def _is_battery_record(cs_row: dict) -> bool:
    """电池范围判定（业务口径：只做电池类目，充电器/壳/线缆等配件不做）。

    ① 前缀必须 CS-：DF=充电器/适配器、CF=对讲机壳、AS=扫描枪线缆（实证
       604 条全配件）；店铺存量 SKU 与履约 SkuResolver 同锚 CS- 前缀。
    ② 历史上架类目白名单（_CATEGORY_SKU_CODE）直接放行——Notebook 等类目
       存在 capacity/battery_type 全空的真电池（店铺一直在卖）。
    ③ 新类目双判据：无配件词 且 capacity/battery_type 至少一项非空
       （实证：Electric eBike/Power Bank 等 22 个新类目 100% 有容量=真电池；
        Screwdriver/Heli/Paintball/Water Gun 全空=非电池）。
    """
    if not (cs_row.get("cs_id") or "").startswith("CS-"):
        return False
    cat = (cs_row.get("category") or "").strip()
    if cat in _CATEGORY_SKU_CODE:
        return True
    low = cat.lower()
    if any(w in low for w in _NON_BATTERY_KW):
        return False
    return bool((cs_row.get("capacity") or "").strip()
                or (cs_row.get("battery_type") or "").strip())


def _dec(v: Any) -> Decimal | None:
    if v is None or v == "":
        return None
    try:
        return Decimal(str(v))
    except Exception:  # noqa: BLE001
        return None


class CsShopifySyncService:
    """CS 产品库 → Shopify：对账（diff）+ 受控执行（apply）。"""

    def __init__(self, store_service: StoreService | None = None,
                 product_service: ProductService | None = None):
        self._stores = store_service or StoreService()
        self._products = product_service or ProductService()
        # 图片外链探测缓存（同 cs_id 多品牌记录只探测一次，实证 7452 行多品牌）
        self._img_cache: dict[str, list[str]] = {}

    def _probe_images(self, cs_id: str, http: httpx.Client) -> list[str]:
        """探测并缓存该 cs_id 的图库外链（head 复用长连接；异常按无图处理不阻断建品）。"""
        if cs_id not in self._img_cache:

            def _head(u: str) -> bool:
                r = http.head(u)
                return r.status_code == 200

            self._img_cache[cs_id] = cs_image_urls(cs_id, _head)
        return self._img_cache[cs_id]

    # ==================================================================
    # CS 产品库（bmai 镜像，只读）
    # ==================================================================
    @staticmethod
    def load_cs_catalog() -> dict[tuple[str, str], dict]:
        """记录级目录：key=(cs_id, brand.lower())。

        CS 源头粒度即记录级——同一 cs_id 多品牌 = 多条独立产品记录
        （实证 7452/22143 行多品牌），店铺上架粒度忠实映射它。
        """
        with get_cs_engine().connect() as c:
            rows = c.execute(text(f"SELECT {_CS_COLS} FROM cs_product")).all()
        catalog: dict[tuple[str, str], dict] = {}
        for r in rows:
            cs_id = str(r[0] or "").strip()
            if not cs_id:
                continue
            brand = str(r[1] or "").strip()
            catalog[(cs_id, brand.lower() or "-")] = {
                "cs_id": cs_id, "brand": brand,
                "part_no": str(r[2] or "").strip(), "fit_model": str(r[3] or "").strip(),
                "capacity": str(r[4] or "").strip(), "voltage": str(r[5] or "").strip(),
                "battery_type": str(r[6] or "").strip(), "dimension": str(r[7] or "").strip(),
                "net_weight_g": int(r[8] or 0), "gross_weight_g": int(r[9] or 0),
                "bar_code": str(r[10] or "").strip(),
                "retail": _dec(r[11]), "status": int(r[12] or 0),
                "category": str(r[13] or "").strip(),
                "wh_value": _dec(r[14]),
            }
        return catalog

    @staticmethod
    def source_grams(cs_row: dict) -> int:
        """发货重量：毛重优先，净重兜底（实证店铺历史 grams 与该口径一致，漂移 0）。"""
        return int(cs_row["gross_weight_g"] or cs_row["net_weight_g"] or 0)

    @staticmethod
    def refresh_cs_catalog(rcustomerno: str) -> dict:
        """触发 bmai CS 产品镜像刷新（CIM Excel 导出 → cs_product upsert）。"""
        from bmai.services.cs.sync import sync_products

        synced, errors = sync_products(str(rcustomerno))
        return {"synced": synced, "errors": errors}

    # ==================================================================
    # 内部全量 diff（apply 执行的依据；不带样本截断）
    # ==================================================================
    def _compute(self, store_id: int, price_mode: str = "report") -> dict:
        catalog_all = self.load_cs_catalog()
        catalog: dict[tuple[str, str], dict] = {}
        excluded_non_battery: list[dict] = []
        for k, v in catalog_all.items():
            if _is_battery_record(v):
                catalog[k] = v
            else:
                excluded_non_battery.append({"cs_id": v["cs_id"], "category": v["category"]})
        on_sale = {k: v for k, v in catalog.items() if v["status"] == 1}
        by_cs: dict[str, list[str]] = {}
        for (csid, _bl) in catalog:
            by_cs.setdefault(csid, []).append(_bl)

        with session_scope() as s:
            rows = s.execute(
                text("SELECT shopify_variant_id, sku, price, grams, barcode, shopify_product_id "
                     "FROM product_variants WHERE store_id = :sid"),
                {"sid": store_id},
            ).all()

        anchored: dict[str, list] = {}
        unanchored = 0
        for vid, sku, price, grams, barcode, spid in rows:
            sku = (sku or "").strip()
            m = _CS_ID_RE.match(sku)
            if not m:
                unanchored += 1
                continue
            parts = sku.split("_")
            anchored.setdefault(m.group(1), []).append({
                "vid": vid, "sku": sku, "price": _dec(price), "grams": int(grams or 0),
                "barcode": (barcode or "").strip(), "spid": spid,
                "bseg": parts[1].lower() if len(parts) >= 2 else "",
            })

        # ---- 记录级配对：SKU 品牌段精确匹配优先；csid 单记录容错（历史品牌段差异）；----
        # ---- 多记录品牌段不匹配 → brand_mismatch 报告（不动店铺数据）                ----
        matched: dict[tuple[str, str], list] = {}
        brand_mismatch: list[dict] = []
        for csid, group in anchored.items():
            rec_brands = by_cs.get(csid) or []
            for v in group:
                b = v["bseg"]
                if b and b in rec_brands:
                    matched.setdefault((csid, b), []).append(v)
                elif len(rec_brands) == 1:
                    matched.setdefault((csid, rec_brands[0]), []).append(v)
                elif rec_brands:
                    brand_mismatch.append({
                        "sku": v["sku"], "cs_id": csid, "sku_brand": b,
                        "cs_brands": sorted(rec_brands)[:6],
                    })

        to_create: list[dict] = []
        to_update: list[dict] = []
        to_archive: list[dict] = []
        orphans: list[str] = []
        suspicious: list[dict] = []
        price_drift = unchanged = barcode_fill = barcode_conflict = 0
        seen_handles: set[str] = set()

        for key, cs_row in on_sale.items():
            group = matched.get(key)
            if group is None:
                if (cs_row.get("category") or "").strip() in _EXCLUDED_CATEGORIES:
                    continue  # 品类收缩黑名单：三类不建新品（存量已 DRAFT）
                payload = self.build_new_product_payload(cs_row)
                # 批内 handle 去重（不同记录生成相同 slug 时加序号后缀）
                h = payload["handle"]
                if h in seen_handles:
                    i = 2
                    while f"{h}-{i}" in seen_handles:
                        i += 1
                    payload["handle"] = f"{h}-{i}"
                seen_handles.add(payload["handle"])
                to_create.append({
                    "cs_id": key[0], "brand": cs_row["brand"], "payload": payload,
                })
                continue
            retail = cs_row["retail"]
            src_grams = self.source_grams(cs_row)
            src_bar = cs_row["bar_code"]
            for v in group:
                fields: dict[str, Any] = {}
                # 条码：只补空；都有但不同 → 计数不动（实证冲突=0，防御性保留）
                if not v["barcode"] and src_bar:
                    fields["barcode"] = src_bar
                    barcode_fill += 1
                elif v["barcode"] and src_bar and v["barcode"] != src_bar:
                    barcode_conflict += 1
                # 重量：双方都有且不同才对齐
                if src_grams > 0 and v["grams"] > 0 and v["grams"] != src_grams:
                    fields["grams"] = src_grams
                # 价格：店铺缺价 → 补零售价（两模式通用）；已有价漂移 → 按模式
                if retail is not None and retail > 0:
                    if v["price"] is None or v["price"] <= 0:
                        fields["price"] = str(retail)
                    elif v["price"] != retail:
                        price_drift += 1
                        pct = abs(float(v["price"]) - float(retail)) / float(retail)
                        if pct > _SUSPICIOUS_PCT:
                            suspicious.append({
                                "sku": v["sku"], "shopify_price": float(v["price"]),
                                "cs_retail": float(retail), "deviation_pct": round(pct * 100, 1),
                            })
                        if price_mode == "overwrite":
                            fields["price"] = str(retail)
                if fields:
                    to_update.append({"vid": v["vid"], "sku": v["sku"], "fields": fields})
                else:
                    unchanged += 1

        for csid, group in anchored.items():
            rec_brands = by_cs.get(csid)
            if rec_brands is None:
                orphans.append(csid)
                continue
            for bl in rec_brands:  # 记录级停产报告（该品牌记录停产且店铺仍有其变体在售）
                if catalog[(csid, bl)]["status"] != 1 and matched.get((csid, bl)):
                    to_archive.append({
                        "cs_id": csid, "brand": catalog[(csid, bl)]["brand"],
                        "reason": "cs_discontinued",
                        "variant_skus": [v["sku"] for v in matched[(csid, bl)]][:5],
                        "shopify_product_ids": sorted({v["spid"] for v in matched[(csid, bl)]}),
                    })

        suspicious.sort(key=lambda x: -x["deviation_pct"])
        return {
            "catalog": catalog, "on_sale": on_sale, "by_cs": by_cs,
            "anchored": anchored, "unanchored": unanchored, "variant_total": len(rows),
            "to_create": to_create, "to_update": to_update, "to_archive": to_archive,
            "orphans": orphans, "suspicious": suspicious, "price_drift": price_drift,
            "unchanged": unchanged, "barcode_fill": barcode_fill,
            "barcode_conflict": barcode_conflict, "brand_mismatch": brand_mismatch,
            "excluded_non_battery": excluded_non_battery,
        }

    # ==================================================================
    # 公开对账预览（REST；样本化，响应体可控）
    # ==================================================================
    def diff(self, store_id: int, price_mode: str = "report", sample: int = 50) -> dict:
        if price_mode not in ("report", "overwrite"):
            raise ValueError(f"未知 price_mode: {price_mode}（report | overwrite）")
        c = self._compute(store_id, price_mode)
        return {
            "store_id": store_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "price_mode": price_mode,
            "cs_catalog": {"records": len(c["catalog"]), "unique_cs_ids": len(c["by_cs"]),
                           "on_sale_records": len(c["on_sale"]),
                           "discontinued_records": len(c["catalog"]) - len(c["on_sale"]),
                           "excluded_non_battery": len(c["excluded_non_battery"])},
            "store_side": {"variants": c["variant_total"],
                           "anchored": c["variant_total"] - c["unanchored"],
                           "unanchored": c["unanchored"], "unique_cs_ids": len(c["anchored"])},
            "plan": {
                "to_create": {
                    "count": len(c["to_create"]),
                    "items": [self._create_summary(i) for i in c["to_create"][:sample]],
                },
                "to_update": {
                    "count": len(c["to_update"]),
                    "items": c["to_update"][:sample],
                    "barcode_fill": c["barcode_fill"], "barcode_conflict": c["barcode_conflict"],
                },
                "to_archive": {"count": len(c["to_archive"]), "items": c["to_archive"][:sample]},
                "orphans": {"count": len(c["orphans"]), "items": c["orphans"][:20]},
                "brand_mismatch": {"count": len(c["brand_mismatch"]),
                                   "items": c["brand_mismatch"][:20]},
                "excluded_non_battery": {"count": len(c["excluded_non_battery"]),
                                         "items": c["excluded_non_battery"][:20]},
                "unchanged": c["unchanged"],
            },
            "price_report": {
                "mode": "report-only" if price_mode == "report" else "overwrite",
                "note": "店铺为独立零售定价体系（实证 99.8% 与 CS 建议零售价不同），默认不改价，仅报告",
                "drift_count": c["price_drift"],
                "suspicious_count": len(c["suspicious"]),
                "suspicious": c["suspicious"][:20],
            },
        }

    @staticmethod
    def _create_summary(item: dict) -> dict:
        p = item["payload"]
        v = p["variants"][0]
        return {"cs_id": item["cs_id"], "brand": item.get("brand"), "title": p["title"],
                "handle": p["handle"], "sku": v.get("sku"), "price": v.get("price"),
                "grams": v.get("grams"), "barcode": v.get("barcode")}

    # ==================================================================
    # 新品 payload（营销字段只在创建时生成，之后永不覆盖）
    # ==================================================================
    def build_new_product_payload(self, cs_row: dict) -> dict:
        """对齐店铺既有上架格式（实证 22k 老品同构，2026-10-31）。"""
        brand = cs_row["brand"]
        fits = [f.strip() for f in re.split(r"[,;/]", cs_row["fit_model"]) if f.strip()]
        pnos = [p.strip() for p in re.split(r"[,;/]", cs_row["part_no"]) if p.strip()]
        name_bits = ([brand] if brand else []) + fits + pnos or [cs_row["cs_id"]]
        title = ("Battery for " + " ".join(name_bits))[:255]
        handle = self._slug("battery for " + " ".join(name_bits))[:100] or cs_row["cs_id"].lower()

        grams = self.source_grams(cs_row)
        # 存量 4 段 SKU 格式：CS-{csid}_{Brand}_{类目码}_0（履约正则前缀锚定，段数不敏感）
        sku_brand = (brand or "").replace("_", " ").strip() or "Battery"
        variant: dict[str, Any] = {
            "sku": f"{cs_row['cs_id']}_{sku_brand}_{_CATEGORY_SKU_CODE.get(cs_row.get('category', ''), 0)}_0",
            # 存量规则：option1=容量（如 2600mAh），缺容量退回 Shopify 默认
            "option1": (cs_row.get("capacity") or "").strip() or "Default Title",
            "inventory_management": "shopify",    # 进 inventory 体系（库存同步任务接管）
        }
        if cs_row["retail"] and cs_row["retail"] > 0:
            variant["price"] = str(cs_row["retail"])
        if cs_row["bar_code"]:
            variant["barcode"] = cs_row["bar_code"]
        if grams > 0:
            variant["grams"] = grams

        return {
            "title": title,
            "handle": handle,                     # 幂等键：重跑/并发防重建
            "vendor": _STORE_VENDOR,              # 店铺统一自有品牌（存量实证）
            # 存量规则实证：product_type = "{CS 类目} Battery"（如 Vacuum Battery）
            "product_type": f"{(cs_row.get('category') or '').strip()} Battery".strip(),
            "tags": "",
            "body_html": self._build_body_html(cs_row),
            "variants": [variant],
            # v2.2（DeepSeek 审查 2026-11-05）：显式命名选项，Shopify 默认名
            # "Title" 会裸露在变体选择器上；Capacity 与 option1 容量口径一致
            "options": [{"name": "Capacity"}],
            # v2.2：独立 SEO 描述（定义句 155 字符），阻断 Dawn 默认取 body
            # 开头导致的徽章文字污染 meta description
            "metafields": [{
                "namespace": "seo", "key": "description",
                "value": self._entity_text(cs_row)[:155],
                "type": "single_line_text_field",
            }],
        }

    @staticmethod
    def _slug(s: str) -> str:
        s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
        return re.sub(r"-{2,}", "-", s)

    @staticmethod
    def _build_body_html(cs_row: dict) -> str:
        """详情页 body v2 分区模板（2026-11-03）：

        信任徽章条 → 规格表 → 兼容列表（空值省略规则保留）→ 安全警示
        → 品牌卖点 → FAQ 折叠收尾（购买提示已并入 FAQ 首条，2026-11-03）。
        全部内联样式，Shopify 描述区安全。"""
        S = CsShopifySyncService
        return "\n".join(s for s in (
            S._sec_highlights(),
            S._entity_sentence(cs_row),
            S._spec_tables_html(cs_row),
            S._sec_compatible(cs_row),
            S._sec_safety(),
            S._sec_selling(),
            S._sec_faq(),
        ) if s)

    @staticmethod
    def _entity_sentence(cs_row: dict) -> str:
        """自包含定义句（AI 搜索适配 2026-11-03）：一句话含全部关键实体
        （容量/电压/类型/品牌/型号/件号），是 AI 摘要的最小可引用单元；
        缺失片段自动省略，型号取前 2、件号取前 3，余量以 "and more" 收口。"""
        def uniq(seq) -> list[str]:
            seen: set[str] = set()
            return [x for x in seq if not (x in seen or seen.add(x))]

        specs = " ".join((cs_row.get(k) or "").strip()
                         for k in ("capacity", "voltage", "battery_type")
                         if (cs_row.get(k) or "").strip())
        head = ("This is a " + specs + " replacement battery").replace("  ", " ")

        brand = cs_row["brand"] or cs_row["cs_id"]
        fits = uniq(f.strip() for f in re.split(r"[,;/]", cs_row["fit_model"] or "") if f.strip())
        pnos = uniq(p.strip() for p in re.split(r"[,;/]", cs_row["part_no"] or "") if p.strip())

        seg = (f"for {_esc(brand)} {_esc(', '.join(fits[:2]))}"
               + (" and more" if len(fits) > 2 else "")) if fits \
            else f"for {_esc(brand)} devices"
        if pnos:
            seg += (", compatible with battery part numbers "
                    + _esc(", ".join(pnos[:3]))
                    + (" and more" if len(pnos) > 3 else ""))
        return ('<p style="margin:10px 0 0;font-size:14px;color:#1B2A41;'
                'line-height:1.6;">' + head + " " + seg + ".</p>\n")

    @staticmethod
    def _entity_text(cs_row: dict) -> str:
        """定义句纯文本：供 seo.description（155 字符截断）复用，阻断
        Dawn 默认取 body 开头导致的徽章污染 meta（2026-11-05）。"""
        html = CsShopifySyncService._entity_sentence(cs_row)
        return re.sub(r"<[^>]+>", "", html).strip()

    @staticmethod
    def _sec_highlights() -> str:
        """页首信任徽章条：保修/退换/发货/认证（政策占位见 _POLICY）。"""
        def badge(txt: str) -> str:
            return (f'<span style="display:inline-block;background:#F4F6F8;'
                    f'border:1px solid #D9E2EC;border-radius:6px;padding:5px 12px;'
                    f'margin:0 6px 6px 0;font-size:13px;font-weight:600;'
                    f'color:#1B2A41;">{txt}</span>')
        return ('<div style="margin:0 0 14px;line-height:1.6;">'
                + badge(_esc(_POLICY["warranty"]))
                + badge(_esc(_POLICY["returns"]))
                + badge(_esc(_POLICY["shipping"]))
                + badge(_esc(_POLICY["certs"]))
                + "</div>\n")

    @staticmethod
    def _sec_compatible(cs_row: dict) -> str:
        """兼容区（v2.2 收敛）：单 h3 Compatibility + 行内标签组，
        Brand 单值行内、Model/Part Number 多值列表（内容口径与 2026-11-03
        用户确认版一致）；型号/件号空时对应组省略；超 10 项 column-width
        自适应列；多值去重保序（源数据偶见重复型号）。"""
        def uniq(seq) -> list[str]:
            seen: set[str] = set()
            return [x for x in seq if not (x in seen or seen.add(x))]

        def label(txt: str) -> str:
            return f'<div style="margin:6px 0 0;"><b>{txt}:</b></div>'

        def ul(items: list[str]) -> str:
            extra = "column-width:170px;column-gap:28px;" if len(items) > 10 else ""
            lis = "".join(f"<li><b>{_esc(i)}</b></li>\n" for i in items)
            return (f'<ul style="margin:4px 0 0;padding-left:22px;{extra}">\n'
                    f"{lis}</ul>\n")

        fits = uniq(f.strip() for f in re.split(r"[,;/]", cs_row["fit_model"]) if f.strip())
        pnos = uniq(p.strip() for p in re.split(r"[,;/]", cs_row["part_no"]) if p.strip())
        brand = cs_row["brand"] or cs_row["cs_id"]
        out = [_h3("Compatibility"),
               '<div style="margin:6px 0 0;"><b>Compatible Brand:</b> '
               + _esc(brand) + "</div>"]
        if fits:
            out.append(label("Compatible Model") + ul(fits))
        if pnos:
            out.append(label("Compatible Battery Part Number") + ul(pnos))
        return '<div style="margin:0 0 6px;">' + "".join(out) + "</div>\n"

    @staticmethod
    def _sec_safety() -> str:
        """电池安全警示（品类刚需）：浅黄警示框 + 左侧粗边框。"""
        items = (
            "Do not disassemble, puncture or modify the battery.",
            "Never short-circuit the terminals or expose to heat / fire.",
            "Do not mix with different batteries or chargers.",
            "Recycle used batteries at designated collection points.",
        )
        lis = "".join(f'<li style="margin:2px 0;">{t}</li>' for t in items)
        return (
            _h3("&#9888; Safety Warnings")
            + '<div style="background:#FFF8E1;border-left:4px solid #B7791F;'
              'border-radius:4px;padding:10px 14px;margin:0 0 6px;color:#52606D;'
              'font-size:14px;line-height:1.6;">'
            + f'<ul style="margin:0;padding-left:20px;">{lis}</ul></div>\n'
        )

    @staticmethod
    def _sec_selling() -> str:
        """品牌卖点 + 合规声明（UN38.3/MSDS/ISO9001 真实口径；CE/RoHS 未做过不宣称）。"""
        points = (
            ("Grade A Cells", "Premium cells with stable discharge and low self-discharge."),
            ("Real Capacity", "Capacity tested to match or exceed the original battery."),
            ("Strict QC", "Every battery passes charging/discharging and safety checks."),
        )
        rows = "".join(
            f'<div style="margin:6px 0;"><b style="color:#1B2A41;">&#10003; {t}</b>'
            f' <span style="color:#52606D;font-size:14px;">— {d}</span></div>'
            for t, d in points)
        return (
            _h3("Why Choose Estry")
            + '<div style="background:#F4F6F8;border-radius:8px;padding:10px 14px;'
              'margin:0 0 6px;">' + rows + "</div>\n"
            + '<div style="color:#52606D;font-size:14px;margin:8px 0 0;">'
              "UN38.3 tested for safe transport. MSDS available upon request. "
              "Manufactured in an ISO9001 certified facility.</div>\n"
        )

    @staticmethod
    def _sec_faq() -> str:
        """FAQ 折叠（details/summary）：不支持折叠的主题自然展开，降级安全。"""
        faqs = (
            ("How do I confirm this battery fits my device?",
             "Match your device against the <b>Compatible Model</b> list above, or "
             "compare the part number printed on your original battery. Still unsure? "
             "Email us with your battery details or photos and we will help you confirm."),
            ("What is the warranty policy?",
             f"This battery is covered by a {_POLICY['warranty'].lower()} against "
             f"manufacturing defects, plus {_POLICY['returns'].lower()} for peace of mind."),
            ("How fast will my order arrive?",
             "In-stock orders ship from our US warehouse within 48 hours on business days."),
        )
        out = [_h3("FAQ")]
        for q, a in faqs:
            out.append(
                '<details style="margin:6px 0;border:1px solid #D9E2EC;'
                'border-radius:6px;padding:8px 12px;">'
                + f'<summary style="font-weight:600;color:#1B2A41;'
                  f'cursor:pointer;">{_esc(q)}</summary>'
                + f'<p style="margin:8px 0 2px;color:#52606D;font-size:14px;'
                  f'line-height:1.6;">{a}</p></details>')
        return "".join(out) + "\n"

    @staticmethod
    def _spec_tables_html(cs_row: dict) -> str:
        """Battery Specifications 规格表（v2：单表格、边框+灰底标签列、
        100% 宽度移动端自适应）；空字段跳行，全空则整段省略。

        数据加工口径不变：Weight 一位小数；Dimension 去尾零 * 连接；
        Rate 优先源 wh，缺失按 capacity×voltage 推导（老品实证口径）。"""
        # Weight: 270 → "270.0g"（存量口径一位小数）
        w = int(cs_row.get("gross_weight_g") or cs_row.get("net_weight_g") or 0)
        weight = f"{float(w):.1f}g" if w > 0 else ""
        # Dimension: "69.40 x 37.00 x 37.00mm" → "69.4*37.0*37.0mm"（去尾零、* 连接）
        dim = ""
        nums = re.findall(r"\d+(?:\.\d+)?", cs_row.get("dimension") or "")
        if len(nums) >= 2:
            dim = "*".join(str(float(n)) for n in nums[:3]) + "mm"
        # Rate: wh 源值优先；缺失(0)时按 capacity×voltage 推导（2.6Ah×14.4V=37.44Wh
        # 与老品 Rate 精确吻合——源 wh 大面积缺失，老品页为人工同口径算出）
        wh = cs_row.get("wh_value")
        rate = f"{float(wh):.2f}Wh" if wh is not None and float(wh) > 0 else ""
        if not rate:
            m_cap = re.match(r"([\d.]+)\s*mAh", (cs_row.get("capacity") or ""), re.I)
            m_volt = re.match(r"([\d.]+)", cs_row.get("voltage") or "")
            if m_cap and m_volt:
                rate = f"{float(m_cap.group(1)) / 1000 * float(m_volt.group(1)):.2f}Wh"

        rows = ([("Type:", (cs_row.get("battery_type") or "").strip()),
                 ("Weight:", weight), ("Dimension:", dim)]
                + [("Category:", (cs_row.get("category") or "").strip()),
                   ("Voltage:", (cs_row.get("voltage") or "").strip()),
                   ("Rate:", rate)])
        rows = [(a, b) for a, b in rows if b]
        if not rows:
            return ""

        trs = "".join(
            '<tr><td style="width:40%;background:#F4F6F8;border:1px solid #D9E2EC;'
            "padding:6px 10px;font-weight:700;color:#1B2A41;\">" + _esc(label)
            + '</td><td style="border:1px solid #D9E2EC;padding:6px 10px;'
              'color:#1B2A41;\">' + _esc(val) + "</td></tr>\n"
            for label, val in rows)
        return (
            _h3("Battery Specifications")
            + '<table width="100%" cellspacing="0" cellpadding="0" '
              'style="border-collapse:collapse;margin:0 0 4px;font-size:14px;">'
            + f"<tbody>\n{trs}</tbody></table>\n"
        )

    # ==================================================================
    # 受控执行
    # ==================================================================
    def apply(
        self,
        store_id: int,
        dry_run: bool = True,
        price_mode: str = "report",
        publish_status: str = "active",        # active | draft
        max_ops: int = 200,                    # create/update 各自的每轮上限（限流收敛）
        only_cs_id: str | None = None,         # 只处理该 cs_id 的新品（单点建品/修复）
    ) -> dict:
        """执行对账结果。dry_run=True 只返回计划统计，不发任何 Shopify 写请求。

        only_cs_id 指定时只创建该 cs_id 的产品、跳过存量 update（单点操作）。
        """
        if price_mode not in ("report", "overwrite"):
            raise ValueError(f"未知 price_mode: {price_mode}（report | overwrite）")
        if publish_status not in ("active", "draft"):
            raise ValueError(f"未知 publish_status: {publish_status}（active | draft）")

        c = self._compute(store_id, price_mode)
        creates = c["to_create"]
        if only_cs_id:
            creates = [i for i in creates if i["cs_id"] == only_cs_id]
        summary: dict[str, Any] = {
            "store_id": store_id, "dry_run": dry_run, "price_mode": price_mode,
            "publish_status": publish_status, "max_ops": max_ops,
            "only_cs_id": only_cs_id,
            "to_create": len(creates), "to_update": len(c["to_update"]),
            "created": 0, "updated": 0, "skipped_existing": 0, "failed": 0, "errors": [],
            "images_attached": 0, "images_missing": 0,
        }
        if dry_run:
            return summary

        client = self._stores.get_client(store_id)
        rest = ShopifyRest(client)
        # 图库外链探测通道（cameronsino.co 直连，不经 Shopify 代理）
        img_http = httpx.Client(timeout=10, follow_redirects=True, headers=_CS_IMG_HEADERS)
        try:
            # ---- 新品发布（幂等：handle 已在店铺存在 → 跳过建品、补本地镜像） ----
            for item in creates:
                if summary["created"] + summary["skipped_existing"] >= max_ops:
                    break
                try:
                    existing = rest.product_by_handle(item["payload"]["handle"])
                    if existing:
                        summary["skipped_existing"] += 1
                        self._products._upsert_product(store_id, existing)
                        continue
                    payload = dict(item["payload"])
                    payload["status"] = publish_status
                    # 图片：cameronsino.co 外链直挂（Shopify 建品时自动拉取转存
                    # cdn.shopify.com，与老品同源）；无图品照常建（约 2% 图库缺失）
                    urls = self._probe_images(item["cs_id"], img_http)
                    if urls:
                        # alt=产品标题（2026-11-05 DeepSeek 审查：裸 alt 对 SEO/
                        # 无障碍双输；标题已含品牌型号关键词，第 N 张加序号）
                        _alt = payload["title"]
                        payload["images"] = [
                            {"src": u, "alt": _alt if n == 0 else f"{_alt} - {n + 1}"}
                            for n, u in enumerate(urls)]
                        summary["images_attached"] += 1
                    else:
                        summary["images_missing"] += 1
                        logger.info(f"[cs-sync] {item['cs_id']} 图库无图，裸建品")
                    created = rest.create_product(payload)
                    self._products._upsert_product(store_id, created)
                    summary["created"] += 1
                except Exception as e:  # 单品失败不阻断整批
                    summary["failed"] += 1
                    summary["errors"].append(
                        f"create {item['cs_id']}/{item.get('brand')}: {str(e)[:180]}")
                    logger.warning(f"[cs-sync] create {item['cs_id']}/{item.get('brand')} 失败: {e}")

            # ---- 存量变体字段对齐（条码补空 / 重量对齐 / 按模式的价格） ----
            for item in ([] if only_cs_id else c["to_update"]):
                if summary["updated"] >= max_ops:
                    break
                try:
                    updated = rest.update_variant(item["vid"], item["fields"])
                    self._writeback_variant(store_id, updated)
                    summary["updated"] += 1
                except Exception as e:
                    summary["failed"] += 1
                    summary["errors"].append(f"update {item['sku']}: {str(e)[:180]}")
                    logger.warning(f"[cs-sync] update {item['sku']} 失败: {e}")
        finally:
            img_http.close()
            client.close()
        return summary

    @staticmethod
    def _writeback_variant(store_id: int, variant: dict) -> None:
        """变体更新结果回写本地镜像（仅 touched 字段）。"""
        with session_scope() as s:
            row = s.execute(
                text("SELECT id FROM product_variants WHERE store_id = :sid AND shopify_variant_id = :vid"),
                {"sid": store_id, "vid": variant.get("id")},
            ).scalar_one_or_none()
            if row is None:
                return
            v: ProductVariant = s.get(ProductVariant, row)
            if "barcode" in variant:
                v.barcode = variant.get("barcode") or ""
            if "grams" in variant and variant.get("grams"):
                v.grams = int(variant["grams"])
            if "price" in variant and variant.get("price") not in (None, ""):
                v.price = Decimal(str(variant["price"]))
            v.shopify_updated_at = datetime.now()
