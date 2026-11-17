# -*- coding: utf-8 -*-
"""修复 /collections/all 缺 meta description：theme.liquid 条件输出 + 上传验证。"""
import re
import sys
import time

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

cl = ShopifyRest(StoreService().get_client(1)).client
KEY = "layout/theme.liquid"
DESC = ("Shop all replacement batteries at Estry: medical device, power tool, "
        "laptop and security system batteries compatible with 10,000+ device "
        "models. US warehouse, 12-month warranty, worldwide shipping.")

a = cl.request("GET", "themes/190031036660/assets.json",
               params={"asset[key]": KEY})
src = a["asset"]["value"]

if DESC[:40] in src:
    print("已修复过，跳过")
else:
    old = ('{% if page_description %}\n'
           '      <meta name="description" content="{{ page_description | escape }}">\n'
           '    {% endif %}')
    new = ('{% if page_description %}\n'
           '      <meta name="description" content="{{ page_description | escape }}">\n'
           "    {% elsif request.path == '/collections/all' %}\n"
           f'      <meta name="description" content="{DESC}">\n'
           '    {% endif %}')
    assert old in src, "锚点未命中"
    with open("/home/jason/shopify-admin/deploy/theme_liquid_backup.liquid",
              "w") as f:
        f.write(src)
    cl.request("PUT", "themes/190031036660/assets.json", json_body={
        "asset": {"key": KEY, "value": src.replace(old, new)}})
    print("theme.liquid 已更新（备份: deploy/theme_liquid_backup.liquid）")

time.sleep(20)
r = httpx.get("https://www.estrybattery.com/collections/all",
              headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; "
                                     "x64) Chrome/119.0.0.0 Safari/537.36"},
              timeout=30, follow_redirects=True)
m = re.search(r'<meta name="description" content="(.*?)"', r.text)
print(f"验证 HTTP {r.status_code}: "
      f"{(m.group(1)[:90] + '...') if m else '【仍缺失】'}")
