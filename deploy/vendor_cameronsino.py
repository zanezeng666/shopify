# -*- coding: utf-8 -*-
"""全店 vendor -> Cameron Sino (GTIN品牌一致性, 幂等)。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

cl = ShopifyRest(StoreService().get_client(1)).client
params = {"limit": 250, "status": "active", "fields": "id,vendor"}
ids = []
while True:
    time.sleep(0.9)
    r = cl._client.get("products.json", params=params, auth=cl._auth)
    r.raise_for_status()
    ids += [p["id"] for p in r.json()["products"]
            if p.get("vendor") != "Cameron Sino"]
    link = r.headers.get("Link", "")
    nxt = [y.split(";")[0].strip("<>")
           for y in link.split(",") if 'rel="next"' in y]
    if not nxt:
        break
    params = {"limit": 250, "page_info": nxt[0].split("page_info=")[-1]}
print(f"待改 vendor: {len(ids)} 个产品")

ok = fail = 0
for i, pid in enumerate(ids, 1):
    try:
        time.sleep(0.45)
        r2 = cl._client.put(f"products/{pid}.json", auth=cl._auth,
                            json={"product": {"id": pid,
                                              "vendor": "Cameron Sino"}})
        r2.raise_for_status()
        ok += 1
    except Exception as ex:
        fail += 1
        if fail <= 5:
            print("失败:", pid, str(ex)[:90])
    if i % 500 == 0:
        print(f"进度 {i}/{len(ids)} ok={ok} fail={fail}", flush=True)
print(f"\n完成: ok={ok} fail={fail}")
