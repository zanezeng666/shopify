"""v2 模板真实数据预览：从 CS 镜像挑 3 种形态渲染，输出预览 HTML。

形态：A 型号多（双列网格） B part_no 空（省略规则） C 标准
"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.products.sync_shopify import CsShopifySyncService as S

catalog = S.load_cs_catalog()

def n_models(r):
    return len([x for x in (r.get("fit_model") or "").replace(";", ",").replace("/", ",").split(",") if x.strip()])

a = b = c = None
for (_csid, _bl), r in catalog.items():
    if r.get("status") != 1:
        continue
    pno = (r.get("part_no") or "").strip()
    if a is None and n_models(r) >= 12 and pno:
        a = r
    if b is None and not pno and (r.get("fit_model") or "").strip():
        b = r
    if c is None and pno and 3 <= n_models(r) <= 6:
        c = r
    if a and b and c:
        break

cases = [
    ("A · 多型号（双列网格）+ 件号", a),
    ("B · part_no 为空（Part Number 段自动省略）", b),
    ("C · 标准形态", c),
]
cards = []
for label, row in cases:
    if not row:
        continue
    body = S._build_body_html(row)
    cards.append(f"""
    <div style="max-width:760px;margin:28px auto;background:#fff;border:1px solid #e5e9f0;
                border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(27,58,92,.08);">
      <div style="background:#1B3A5C;color:#fff;padding:14px 20px;font-size:15px;font-weight:600;">
        {label} &nbsp;<span style="opacity:.65;font-weight:400;font-size:13px;">{row["cs_id"]} / {row.get("brand","")}</span>
      </div>
      <div style="padding:18px 20px 22px;">
        <h2 style="font-size:17px;color:#1F2933;margin:0 0 12px;font-weight:700;">
          Battery for {(row.get("brand") or "")} {(row.get("fit_model") or "")[:60]}</h2>
        <div style="color:#B12704;font-size:18px;font-weight:700;margin:0 0 14px;">
          ${(row.get("retail") or 0)} <span style="color:#52606D;font-size:12px;font-weight:400;">USD</span></div>
        {body}
      </div>
    </div>""")

html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bomibattery 详情页模板 v2 预览</title></head>
<body style="margin:0;background:#F4F6F8;font-family:'Helvetica Neue',Arial,sans-serif;">
<div style="text-align:center;padding:22px 10px 4px;color:#1B3A5C;">
  <div style="font-size:20px;font-weight:700;">产品详情页模板 v2 预览</div>
  <div style="font-size:13px;color:#52606D;margin-top:6px;">
    真实 CS 库数据渲染 · 内联样式（Shopify 描述区同规则）· 缩窄窗口可模拟移动端</div>
</div>
{''.join(cards)}
</body></html>"""

with open("/tmp/preview_v2.html", "w", encoding="utf-8") as f:
    f.write(html)
print("cases:", [(lbl, row and row["cs_id"]) for lbl, row in cases])
print("bytes:", len(html))
