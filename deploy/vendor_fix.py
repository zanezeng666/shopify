# -*- coding: utf-8 -*-
"""vendor 红线修复: 全店 Cameron Sino -> Estry (MC feed brand 取自 vendor)。
cursor 翻页逐个 PUT, 幂等断点续跑 (完成的产品 vendor=Estry 不再命中查询)。
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
LOG = open("/home/jason/shopify-admin/deploy/vendor_fix.log", "a",
           encoding="utf-8")

params = {"limit": 250, "status": "active", "vendor": "Cameron Sino",
          "fields": "id,title,vendor"}
done = fail = 0
pages = 0
while True:
    r = cl._client.get("products.json", auth=cl._auth,
                       params=params, timeout=60)
    items = r.json().get("products", [])
    if not items:
        break
    pages += 1
    for p in items:
        ok = False
        for attempt in range(3):
            try:
                r2 = cl._client.put(
                    f"products/{p['id']}.json", auth=cl._auth,
                    json={"product": {"id": p["id"], "vendor": "Estry"}},
                    timeout=30)
                if r2.status_code == 200:
                    ok = True
                    break
            except Exception as e:
                print(f"EXC @{p['id']}: {e}", file=LOG, flush=True)
            time.sleep(1.2 * (attempt + 1))
        done += ok
        fail += (not ok)
        time.sleep(0.45)
    print(f"page{pages}: 累计改 {done} 失败 {fail}", file=LOG, flush=True)
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250,
              "page_info": nxt[0].split("page_info=")[-1],
              "fields": "id,title,vendor"}

print(f"完成: 改 {done} 失败 {fail}", file=LOG, flush=True)
