# -*- coding: utf-8 -*-
"""查看首页 index.json 结构与线上首页现状。"""
import json
import sys
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
v = c.request("GET", "themes/190031036660/assets.json",
              params={"asset[key]": "templates/index.json"})["asset"]["value"]
d = json.loads(v)
out = {"order": d["order"], "sections": {}}
KEEP = ("image", "heading", "subheading", "text", "collection", "caption",
        "description", "button_label", "button_link", "color_scheme",
        "image_height", "desktop_content_position", "show_text_box",
        "text_alignment", "height", "columns_desktop", "products_to_show",
        "columns_mobile", "swipe_on_mobile", "show_view_all", "header")
for k, s in d["sections"].items():
    out["sections"][k] = {"type": s.get("type"),
                          "settings": {kk: vv for kk, vv in s.get("settings", {}).items()
                                       if kk in KEEP and not isinstance(vv, dict)}}
print(json.dumps(out, indent=1, ensure_ascii=False))

req = urllib.request.Request("https://www.estrybattery.com/?fresh=1",
                             headers={"User-Agent": "Mozilla/5.0"})
body = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
import re
print("== 线上首页片段 ==")
for m in re.findall(r"<h2[^>]*>(.{0,80}?)</h2>", body)[:12]:
    print("  h2:", m.strip())
for m in re.findall(r"<h1[^>]*>(.{0,80}?)</h1>", body)[:3]:
    print("  h1:", m.strip())
print("  placeholder图:", body.count("cdn.shopify.com/s/files/1/0913/9098/9705/files/"))
