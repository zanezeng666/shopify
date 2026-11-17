# -*- coding: utf-8 -*-
"""注入 Bing Webmaster meta 验证码到 theme.liquid <head>，线上确认后提示用户回 BWT 点 Verify。"""
import re
import sys
import time

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

TID = 190031036660
CODE = "9D2596B6AD46BCCB5A06FB19F6FD9065"
TAG = f'<meta name="msvalidate.01" content="{CODE}" />'

c = ShopifyRest(StoreService().get_client(1)).client

# 1. 读取 theme.liquid
a = c.request("GET", f"themes/{TID}/assets.json",
              params={"asset[key]": "layout/theme.liquid"}).get("asset", {})
src = a.get("value", "")
print(f"theme.liquid {len(src)} chars")

if "msvalidate.01" in src:
    src = re.sub(r'<meta name="msvalidate.01"[^>]*>', TAG, src)
    print("已存在 msvalidate，更新为新验证码")
else:
    # 插到 </head> 前
    if "</head>" not in src:
        print("!! 未找到 </head>，中止")
        sys.exit(1)
    src = src.replace("</head>", TAG + "\n</head>", 1)
    print("在 </head> 前注入")

c.request("PUT", f"themes/{TID}/assets.json",
          json_body={"asset": {"key": "layout/theme.liquid", "value": src}})
print("PUT 完成，等 CDN 传播...")

# 2. 线上确认
UA = {"User-Agent": "Mozilla/5.0 (compatible; verify/1.0)"}
for i in range(10):
    time.sleep(6 if i else 3)
    r = httpx.get("https://www.estrybattery.com/", headers=UA, timeout=30,
                  follow_redirects=True)
    m = re.search(r'<meta name="msvalidate.01" content="([^"]+)"', r.text)
    print(f"  探测 {i+1}: HTTP {r.status_code} meta={m.group(1) if m else '未出现'}")
    if m and m.group(1).upper() == CODE:
        print("\n=== meta 已上线，请回 Bing Webmaster Tools 点 Verify ===")
        sys.exit(0)
print("!! 60s 内未在首页出现（CDN 缓存可能更久），稍后可手动刷新 BWT 再点 Verify")
