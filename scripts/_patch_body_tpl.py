# -*- coding: utf-8 -*-
"""按行号替换 _build_body_html（字符串字面量含不可见字符，replace 工具失配）。"""
from pathlib import Path

F = Path(r"e:\worksapce\shopify\src\shopify_admin\services\products\sync_shopify.py")
lines = F.read_text(encoding="utf-8").splitlines(keepends=True)

# 校验锚点（0-based：429 行 = "    @staticmethod"，430 = def _build_body_html）
assert lines[429].strip() == "@staticmethod", lines[429]
assert "_build_body_html" in lines[430], lines[430]
assert lines[460].rstrip() == "        )", lines[460]  # 461 行结尾

new_func = '''    @staticmethod
    def _build_body_html(cs_row: dict) -> str:
        """复刻店铺存量 body 模板（实证 22k 老品同构，如 7122951831719）：
        Battery Specifications 双表格 + Compatible 列表 + 认证/Tips 尾段。"""
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def lis(items: list[str]) -> str:
            if not items:
                items = [cs_row["cs_id"]]
            return "".join(f"<li><b>{esc(i)}</b></li>\\n" for i in items)

        spec = CsShopifySyncService._spec_tables_html(cs_row)

        fits = [f.strip() for f in re.split(r"[,;/]", cs_row["fit_model"]) if f.strip()]
        pnos = [p.strip() for p in re.split(r"[,;/]", cs_row["part_no"]) if f.strip()]
        brand = cs_row["brand"] or cs_row["cs_id"]
        return (
            spec
            + "<br><br>- Compatible Brand: <br>\\n"
            + f"<ul><li><b>{esc(brand)}</b></li></ul>\\n"
            + " <br>- Compatible Model: <br>\\n\\t<ul>\\n"
            + f"\\t{lis(fits)}\\t</ul>\\n"
            + "<br>- Compatible Battery Part Number: <br>\\n\\t<ul>\\n"
            + f"\\t{lis(pnos)}\\t</ul>\\n"
            + "<br>- RoHS approved for toxic free.<br>\\n"
            + "<br>- CE and ISO9001 Certificate for quality assurance.<br>\\n"
            + "<br><b>Tips Before Purchase</b><br>\\n"
            + "Please confirm the compatible model and battery part number carefully "
            "before you purchase it. <br>\\n"
            + "If you are not sure, please send email to us with your battery details "
            "or pictures, we will give you professional suggestions.\\n"
        )

    @staticmethod
    def _spec_tables_html(cs_row: dict) -> str:
        """Battery Specifications 双表格（左 Type/Weight/Dimension，右
        Category/Voltage/Rate），逐字复刻存量页首模板；空字段跳行，
        两表全空则整段省略（退化为纯列表形态）。"""
        def esc(x: Any) -> str:
            return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # Weight: 270 → "270.0g"（存量口径一位小数）
        w = int(cs_row.get("gross_weight_g") or cs_row.get("net_weight_g") or 0)
        weight = f"{float(w):.1f}g" if w > 0 else ""
        # Dimension: "69.40 x 37.00 x 37.00mm" → "69.4*37.0*37.0mm"（去尾零、* 连接）
        dim = ""
        nums = re.findall(r"\\d+(?:\\.\\d+)?", cs_row.get("dimension") or "")
        if len(nums) >= 2:
            dim = "*".join(str(float(n)) for n in nums[:3]) + "mm"
        # Rate: wh 源值优先；缺失(0)时按 capacity×voltage 推导（2.6Ah×14.4V=37.44Wh
        # 与老品 Rate 精确吻合——源 wh 大面积缺失，老品页为人工同口径算出）
        wh = cs_row.get("wh_value")
        rate = f"{float(wh):.2f}Wh" if wh is not None and float(wh) > 0 else ""
        if not rate:
            m_cap = re.match(r"([\\d.]+)\\s*mAh", (cs_row.get("capacity") or ""), re.I)
            m_volt = re.match(r"([\\d.]+)", cs_row.get("voltage") or "")
            if m_cap and m_volt:
                rate = f"{float(m_cap.group(1)) / 1000 * float(m_volt.group(1)):.2f}Wh"

        left = [("Type:", (cs_row.get("battery_type") or "").strip()),
                ("Weight:", weight), ("Dimension:", dim)]
        right = [("Category:", (cs_row.get("category") or "").strip()),
                 ("Voltage:", (cs_row.get("voltage") or "").strip()), ("Rate:", rate)]
        left = [(a, b) for a, b in left if b]
        right = [(a, b) for a, b in right if b]
        if not left and not right:
            return ""

        def table(rows: list, left_side: bool) -> str:
            trs = []
            for i, (label, val) in enumerate(rows):
                lab = (f'<td width="40%"><b>{label}</b></td>' if i == 0
                       else f'<td class="detail-tit"><b>{label}</b></td>')
                if i == 0 and left_side:
                    cell = f'<td style="text-align: left;" class="detail-tit">{esc(val)}</td>'
                else:
                    cell = (f'<td class="detail-tit">{esc(val)}</td>' if i == 0
                            else f'<td class="detail-val">{esc(val)}</td>')
                trs.append(f"<tr>\\n{lab}\\n{cell}\\n</tr>\\n")
            if left_side:
                head = ('<table style="float: left;" border="0" cellspacing="5" '
                        'cellpadding="5" width="100%">')
            else:
                head = ('<table border="0" cellspacing="0" cellpadding="5" '
                        'style="float: left;" width="100%">')
            return f"{head}\\n<tbody>\\n{''.join(trs)}</tbody>\\n</table>\\n"

        return (
            "Battery Specifications <br> <br>\\n"
            '<div style="display: flex;" width="100%">\\n'
            + table(left, True)
            + table(right, False)
            + "</div>\\n"
        )
'''

lines[429:461] = [new_func]
F.write_text("".join(lines), encoding="utf-8")
print("OK, replaced lines 430-461")
