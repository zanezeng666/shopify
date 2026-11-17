# -*- coding: utf-8 -*-
"""补验：公告条文案 / 按钮配色体系 / 画廊布局。"""
import sys
import json
import re

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
cl = rest.client

# 1) "Welcome to our store" 出自哪个文件/默认值
for key in ("config/settings_schema.json", "sections/header.liquid",
            "sections/announcement-bar.liquid"):
    try:
        a = cl.request("GET", "themes/190031036660/assets.json",
                       params={"asset[key]": key})
        v = a["asset"]["value"]
        if "Welcome" in v:
            i = v.find("Welcome")
            print(f"== '{key}' 含 Welcome:", " ".join(v[max(0, i-90):i+50].split())[:180])
    except Exception:
        pass

# 2) scheme 按钮/配色（Dawn v16 用 settings.colors_scheme）
cfg = cl.request("GET", "themes/190031036660/assets.json",
                 params={"asset[key]": "config/settings_data.json"})
cur = json.loads(cfg["asset"]["value"]).get("current", {})
sch = cur.get("color_schemes", {})
for sid, s in list(sch.items())[:3]:
    btn = {k: v for k, v in s.items() if "button" in k}
    txt = {k: v for k, v in s.items() if "text" in k or "background" in k}
    print(f"== scheme {sid} 按钮:", btn)
    print(f"   文字/底:", dict(list(txt.items())[:4]))
print("   buttons_radius 等设置:", {k: v for k, v in cur.items() if "button" in k or "corner" in k})

# 3) 产品画廊布局默认
mp = cl.request("GET", "themes/190031036660/assets.json",
                params={"asset[key]": "sections/main-product.liquid"})
mv = mp["asset"]["value"]
m = re.search(r'"id":\s*"gallery_layout".{0,120}?"default":\s*"(\w+)"', mv, re.S)
print("== gallery_layout 默认:", m.group(1) if m else "N/A")
t = re.findall(r'"type":\s*"range"[^}]*"id":\s*"(type_header|type_base)[^"]*"[^}]*?max":\s*(\d+)', mv)
