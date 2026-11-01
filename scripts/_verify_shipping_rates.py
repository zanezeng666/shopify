# -*- coding: utf-8 -*-
"""运费三方对账：确认回调报价与预期一致。

三方独立来源交叉：
  A. 预期基数 —— SQL 直查 cs_shipping_rate（独立取档语义，不经 service 代码）
  B. 回调实报 —— TestClient 模拟 Shopify 结账回调（grams 路径，×1.2 展示价）
  C. bmai 交叉 —— BMAI ShippingRateManager._lookup_price（独立实现）

覆盖：zone 1~9 各抽真实邮编前缀 × 重量档（最小档/档间向上取/中档/尾档/超尾兜底）。
表基数本身已由 bmai 上传时的 CIM 在线校验背书（容差 $0.5）。
"""
import sys

from loguru import logger

logger.remove()

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from bmai.supply_chain.cs_supplier.shipping_rates import ShippingRateManager  # noqa: E402
from shopify_admin.api.app import create_app  # noqa: E402
from shopify_admin.config.settings import settings  # noqa: E402
from shopify_admin.core.database import get_cs_engine  # noqa: E402
from shopify_admin.services.shipping import ShippingRateService  # noqa: E402

WEIGHTS = [113, 300, 2267, 6800, 9999]   # 最小档 / 档间向上取 / 中档 / 尾档 / 超尾兜底
MARKUP = settings.shipping_markup

svc = ShippingRateService()
bmai = ShippingRateManager()
client = TestClient(create_app())

with get_cs_engine().connect() as c:
    zips = dict(c.execute(text(
        "SELECT zone, MIN(zip_prefix) FROM cs_shipping_zone GROUP BY zone")).all())   # zone -> 前缀
    tiers = dict(c.execute(text(
        "SELECT MIN(weight_g), MAX(weight_g) FROM cs_shipping_rate WHERE carrier_code='usps'"
    )).one() and {} or {})  # 占位，实际档界下行再取
    min_w, max_w = c.execute(text(
        "SELECT MIN(weight_g), MAX(weight_g) FROM cs_shipping_rate WHERE carrier_code='usps'"
    )).one()

fails = []
print(f"markup={MARKUP}  usps 档界 {min_w}..{max_w}g")
print(f"{'zone':>4} {'zip':>6} {'w(g)':>6} | {'A:SQL基数':>10} {'B:回调价':>10} {'B/1.2':>8} {'C:bmai':>10} | 判定")
print("-" * 78)

for zone in sorted(zips):
    zp = zips[zone]
    zip5 = zp + "01"
    for w in WEIGHTS:
        # A. 独立 SQL 预期基数（向上取档；超尾档取尾档——与 service 语义对齐）
        with get_cs_engine().connect() as c:
            row = c.execute(text(
                "SELECT price FROM cs_shipping_rate WHERE carrier_code='usps' AND zone=:z "
                "AND weight_g>=:w ORDER BY weight_g LIMIT 1"), {"z": zone, "w": w}).first()
            if row is None:
                row = c.execute(text(
                    "SELECT price FROM cs_shipping_rate WHERE carrier_code='usps' AND zone=:z "
                    "ORDER BY weight_g DESC LIMIT 1"), {"z": zone}).first()
            exp = float(row[0])

        # B. 回调实报（Shopify grams 路径）
        r = client.post("/shopify/callback/carrier-rates", json={"rate": {
            "items": [{"sku": "CS-X_B_0_0", "quantity": 1, "grams": w}],
            "destination": {"country": "US", "postal_code": zip5},
        }})
        rates = {x["service_code"]: x for x in r.json()["rates"]}
        got = rates.get("usps")
        cents = int(got["total_price"]) if got else None
        implied_base = round(cents / 100 / MARKUP, 2) if cents else None

        # C. bmai 独立实现（超重无兜底返回 None，单独标注）
        c_val = bmai._lookup_price("usps", w, zone)

        ok_a = implied_base == round(exp, 2)          # B 折算基数 == A
        # B == A×1.2（分）——与 service 同管道：先 round 到分再 round 到整数（修浮点尾差）
        ok_full = cents == int(round(round(exp * MARKUP, 2) * 100))
        ok_c = (c_val is None) or (abs(c_val - exp) < 0.005)   # C == A（有值时）
        tag = "OK" if (ok_a and ok_full and ok_c) else "MISMATCH"
        if tag != "OK":
            fails.append((zone, zp, w, exp, cents, c_val))
        print(f"{zone:>4} {zp:>6} {w:>6} | {exp:>10.2f} {str(cents):>10} {str(implied_base):>8} "
              f"{str(c_val):>10} | {tag}"
              + ("  (超尾→尾档兜底,bmai无兜底=None)" if w > max_w else ""))

# HK 路线（cs_usps）抽查：service 直接对 SQL
print("-" * 78)
hk_fail = 0
for zone in (2, 5, 8):
    zp = zips[zone]
    q = svc.quote_weight(2267, zp + "01", origin="HK")
    hk = next((x for x in q["carriers"] if x["carrier"] == "cs_usps"), None)
    with get_cs_engine().connect() as c:
        row = c.execute(text(
            "SELECT price FROM cs_shipping_rate WHERE carrier_code='cs_usps' AND zone=:z "
            "AND weight_g>=2267 ORDER BY weight_g LIMIT 1"), {"z": zone}).first()
    exp = float(row[0])
    ok = hk and hk["base_price"] == round(exp, 2) and hk["price"] == round(exp * MARKUP, 2)
    print(f"HK cs_usps zone{zone} {zp}01 2267g: SQL {exp:.2f} -> base {hk['base_price']} "
          f"x1.2 {hk['price']}  {'OK' if ok else 'MISMATCH'}")
    hk_fail += 0 if ok else 1

print("-" * 78)
if fails or hk_fail:
    print(f"FAIL: {len(fails)} 处不一致 + HK {hk_fail} 处")
    for f in fails:
        print("  ", f)
    sys.exit(1)
n = len(zips) * len(WEIGHTS)
print(f"PASS: US 路线 {n} 组 + HK 路线 3 组全部一致（回调 = 表基数 × {MARKUP}）")
