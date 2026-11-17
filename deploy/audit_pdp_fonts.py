# -*- coding: utf-8 -*-
"""产品详情页视觉审查：主题字体配置 + 描述区内联样式全景统计。"""
import sys
import re
import json
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))

# ---------- 1) 主题字体配置（settings_data.json） ----------
cfg = rest.client.request("GET", "themes/190031036660/assets.json",
                          params={"asset[key]": "config/settings_data.json"})
txt = cfg["asset"]["value"]
d = json.loads(txt)
current = d.get("current", {}) or {}
fonts = {k: v for k, v in current.items()
         if "font" in k.lower() or k in ("type_header_font_scale", "type_base_font_scale",
                                         "type_header_spacing", "spacing_sections")}
print("== 主题字体设置:")
for k, v in sorted(fonts.items()):
    print(f"   {k} = {v}")

# ---------- 2) base.css 字体族规则 ----------
a = rest.client.request("GET", "themes/190031036660/assets.json",
                        params={"asset[key]": "assets/base.css"})
css = a["asset"]["value"]
print("\n== base.css 字体规则:")
for pat, label in (
    (r"body\s*,\s*\.body-font[^{]*\{[^}]*\}", "body"),
    (r"\.h1[^{]*,\s*heading-font[^{]*\{[^}]*\}", "heading"),
):
    for m in re.findall(pat, css)[:2]:
        print(f"   [{label}]", " ".join(m.split())[:160])
# :root 变量
root = re.search(r":root\s*\{[^}]+\}", css)
if root:
    vars_ = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", root.group(0)))
    for k in ("--font-heading-family", "--font-body-family", "--font-heading-style",
              "--font-body-style", "--font-heading-weight", "--font-body-weight"):
        if k in vars_:
            print(f"   {k} = {vars_[k]}")
# h1-h6 规则
for tag in ("h1", "h2", "h3", "h4", "h5"):
    for m in re.findall(rf"(?:^|[,\s}}]){tag}(?:\s*,[^{{]*)?\{{([^}}]+)\}}", css)[:1]:
        print(f"   <{tag}>:", " ".join(m.split())[:170])

# ---------- 3) 在线描述 HTML 全景统计 ----------
p = rest.product_by_handle("battery-for-delonghi-colombina-evo-xml510-as00000910")
body = p.get("body_html") or ""
print("\n== 描述 HTML 全景统计 (v2.1 样例):")
print("   font-size 档位:", dict(Counter(re.findall(r"font-size:(\d+)px", body))))
print("   font-weight :", dict(Counter(re.findall(r"font-weight:(\d+)", body))))
print("   color 计数  :", dict(Counter(re.findall(r"color:(#[0-9A-Fa-f]{6})", body))))
print("   background  :", dict(Counter(re.findall(r"background:(#[0-9A-Fa-f]{6})", body))))
print("   border 色   :", dict(Counter(re.findall(r"border(?:-left)?:\d+px solid (#[0-9A-Fa-f]{6})", body))))
print("   border-bottom:", dict(Counter(re.findall(r"border-bottom:\d+px solid (#[0-9A-Fa-f]{6})", body))))
print("   font-family 出现:", len(re.findall(r"font-family", body)))
print("   区块 h3 标题:", re.findall(r"<h3[^>]*>(?:&#\d+; )?([^<]{0,40})", body))
print("   结构块标签:", dict(Counter(re.findall(r"<(details|table|ul|span|b|summary|div|p|h3)[ >]", body))))
