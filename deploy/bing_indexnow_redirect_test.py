# -*- coding: utf-8 -*-
"""测试 Shopify redirect 方案绕过 IndexNow 根目录限制：
1. 创建 redirect /{key}.txt -> 同域 asset 路径（www.estrybattery.com/cdn/...）
2. curl 跟随重定向验证 200 + key 内容
3. IndexNow 小样测试（不带 keyLocation，默认抓根 /{key}.txt）
"""
import json
import re
import sys
import time

import httpx

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

HOST = "www.estrybattery.com"
STATE = "/home/jason/shopify-admin/deploy/idxnow_state.json"
API = "https://api.indexnow.org/indexnow"
UA = {"User-Agent": "Mozilla/5.0 (compatible; EstryIndexNow/1.0)"}

c = ShopifyRest(StoreService().get_client(1)).client
with open(STATE) as f:
    st = json.load(f)
key, asset_key = st["key"], st["asset_key"]
target = f"https://{HOST}/cdn/shop/t/18/assets/{key}.txt"
print(f"key={key}\nredirect target={target}")

# 0. 确认同域 asset 路径可访问
r0 = httpx.get(target, headers=UA, timeout=30, follow_redirects=True)
print(f"asset 同域直访: HTTP {r0.status_code} body={r0.text.strip()[:40]!r}")
if r0.status_code != 200:
    # 带 v 参数再试
    target = st["key_url"].replace("cdn.shopify.com", f"{HOST}/cdn")
    r0 = httpx.get(target, headers=UA, timeout=30, follow_redirects=True)
    print(f"asset 带 v 参数同域: HTTP {r0.status_code} body={r0.text.strip()[:40]!r}")
    if r0.status_code != 200:
        print("!! 同域 asset 均不可达，方案终止")
        sys.exit(1)

# 1. 创建（或更新）redirect
path = f"/{key}.txt"
ex = c.request("GET", "redirects.json", params={"path": path}).get("redirects", [])
body = {"redirect": {"path": path, "target": target}}
if ex:
    rid = ex[0]["id"]
    c.request("PUT", f"redirects/{rid}.json", json_body=body)
    print(f"redirect 更新 id={rid}")
else:
    c.request("POST", "redirects.json", json_body=body)
    print("redirect 创建")

# 2. 验证根路径跟随重定向后 200 + 内容
time.sleep(5)
ok = False
for i in range(5):
    r = httpx.get(f"https://{HOST}/{key}.txt", headers=UA, timeout=30,
                  follow_redirects=True)
    chain = [h.status_code for h in r.history]
    print(f"根路径探测 {i+1}: 链={chain} 最终={r.status_code} "
          f"body={r.text.strip()[:40]!r}")
    if r.status_code == 200 and r.text.strip() == key:
        ok = True
        break
    time.sleep(6)
if not ok:
    print("!! 根路径重定向链未达成 200+key")
    sys.exit(1)

# 3. IndexNow 小样（默认根路径 key）
r = httpx.get(API, params={"url": f"https://{HOST}/", "key": key},
              headers=UA, timeout=60, follow_redirects=True)
print(f"\n小样测试(根路径key): HTTP {r.status_code} {r.text[:100]!r}")
with open(STATE, "w") as f:
    json.dump({**st, "root_key_ok": r.status_code in (200, 202)}, f)
print("结果:", "链路通了，可全量提交" if r.status_code in (200, 202)
      else "仍被拒，需换路线（BWT 人工验证）")
