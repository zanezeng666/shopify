# -*- coding: utf-8 -*-
"""本地验证：CS-TVR500VX 记录 → 新 body_html，规格表段与老品逐行对比。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from decimal import Decimal
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

cs_row = {
    "cs_id": "CS-TVR500VX", "brand": "Amarey", "part_no": "PT-SX-2000L",
    "fit_model": "A800,A900", "capacity": "2600mAh", "voltage": "14.4V",
    "battery_type": "Li-ion", "dimension": "69.40 x 37.00 x 37.00mm",
    "net_weight_g": 200, "gross_weight_g": 270, "bar_code": "4894…",
    "retail": Decimal("32.00"), "status": 1, "category": "Vacuum",
    "wh_value": Decimal("0.00"),
}

body = CsShopifySyncService._build_body_html(cs_row)  # noqa: SLF001
print("===== 生成 body_html =====")
print(body)

# 老品规格表关键行锚点
anchors = [
    "Battery Specifications <br> <br>",
    '<td style="text-align: left;" class="detail-tit">Li-ion</td>',
    "<td class=\"detail-val\">270.0g</td>",
    "<td class=\"detail-val\">69.4*37.0*37.0mm</td>",
    '<td class="detail-tit">Vacuum</td>',
    "<td class=\"detail-val\">14.4V</td>",
    "<td class=\"detail-val\">37.44Wh</td>",
    '<div style="display: flex;" width="100%">',
]
print("===== 锚点校验 =====")
for a in anchors:
    print(("PASS " if a in body else "FAIL "), a)

# 边界：全空 → 纯列表退化（无 Battery Specifications 段）
empty = CsShopifySyncService._spec_tables_html({})  # noqa: SLF001
print("空记录 spec 段为空:", empty == "")
# option1
v = {"capacity": "2600mAh"}
print("option1 有容量:", (v.get("capacity") or "").strip() or "Default Title")
print("option1 空容量:", ({}.get("capacity") or "").strip() or "Default Title")
