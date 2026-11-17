# -*- coding: utf-8 -*-
"""分析 Dawn 主题产品页对描述区(rte)裸标签的实际样式规则。"""
import sys
import re

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))

# 1) 产品描述实际在线 HTML（验证模板渲染）
p = rest.product_by_handle("battery-for-delonghi-colombina-evo-xml510-as00000910")
body = p.get("body_html") or ""
print("== body_html 长度:", len(body))
print("== 内联字号分布:", sorted(set(re.findall(r"font-size:(\d+)px", body))))

# 2) Dawn base.css 的 rte/h 标签规则
a = rest.client.request("GET", "themes/190031036660/assets.json",
                        params={"asset[key]": "assets/base.css"})
css = a["asset"]["value"]
print("\n== base.css 长度:", len(css))
# h1-h6 与 .rte 相关规则
for pat in (r"[^{}]*\.rte[^{}]*\{[^}]*\}",):
    pass
hits = re.findall(r"([^{}]{0,90}\.rte[^{}]{0,60}\{[^}]{0,300}\})", css)
print("\n== .rte 规则 %d 条:" % len(hits))
for h in hits[:14]:
    print("  ", " ".join(h.split())[:200])
# 裸 h3/h2 全局规则
for tag in ("h1", "h2", "h3", "h4"):
    m = re.search(rf"(^|[,\s]){tag}\s*,?[^{{]*{{([^}}]*)}}", css, re.M)
    if m:
        print(f"\n== {tag} 全局规则:", " ".join(m.group(2).split())[:220])
