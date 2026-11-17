# -*- coding: utf-8 -*-
"""核实 DeepSeek PDP 审查报告的关键事实断言。"""
import sys
import json
import re

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
cl = rest.client

# 1) 店铺名（<title>/页脚版权/Organization name 的来源）
shop = cl.request("GET", "shop.json")["shop"]
print("== shop.name =", shop.get("name"), "| domain =", shop.get("primary_domain", {}).get("host"))

# 2) 主题设置：公告条 / logo / 社交链接 / 页脚
cfg = cl.request("GET", "themes/190031036660/assets.json",
                 params={"asset[key]": "config/settings_data.json"})
cur = json.loads(cfg["asset"]["value"]).get("current", {})
for k in sorted(cur):
    if any(s in k for s in ("announcement", "logo", "social", "footer")) \
            and cur[k] not in ("", None, [], {}):
        print(f"   set.{k} = {str(cur[k])[:90]}")
empty_social = [k for k, v in cur.items()
                if k.startswith("social") and k.endswith("link") and v in ("", None)]
print("   空社交链接:", len(empty_social), empty_social[:9])

# 3) 公告条默认值（settings_schema）
sch = cl.request("GET", "themes/190031036660/assets.json",
                 params={"asset[key]": "config/settings_schema.json"})
try:
    schema = json.loads(sch["asset"]["value"])
    for grp in schema:
        for s in grp.get("settings", []):
            if "announcement" in s.get("id", "") and s.get("default"):
                print(f"   schema默认 {s['id']} = {str(s['default'])[:60]}")
except Exception as e:
    print("   schema 解析失败:", e)

# 4) 产品 option 名 + 图片 alt
p = cl.request("GET", "products/15484753215732.json",
               params={"fields": "options,images,title,body_html"})
prod = p["product"]
print("== options:", [(o["name"], o["values"]) for o in prod["options"]])
print("== images alt:", [i.get("alt") for i in prod.get("images", [])][:6])

# 5) meta description / sameAs 生成逻辑
for key in ("snippets/meta-tags.liquid", "layout/theme.liquid"):
    a = cl.request("GET", "themes/190031036660/assets.json", params={"asset[key]": key})
    lv = a["asset"]["value"]
    m = re.search(r'.{0,120}name="description".{0,160}', lv)
    print(f"== {key} meta-desc:", " ".join(m.group(0).split())[:230] if m else "N/A")
    m2 = re.search(r'sameAs.{0,260}?\]', lv, re.S)
    if m2:
        print(f"== {key} sameAs:", " ".join(m2.group(0).split())[:240])
