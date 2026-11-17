"""全库 vendor 品牌切换：Bomibattery/BomiBattery → Estry（幂等可断点）。

PUT 仅携带 vendor 字段（Shopify 部分更新语义，不触碰 body/价格/图片）；
重跑自动跳过已改名产品。后台执行：
  nohup /home/jason/shopify-admin/.venv/bin/python /tmp/rebrand.py >> /tmp/rebrand.log 2>&1 &
"""
import sys
import time
from datetime import datetime

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


pid = scanned = changed = skipped = failed = 0
while True:
    params = {"limit": 250, "fields": "id,vendor"}
    if pid:
        params["since_id"] = pid
    items = c.request("GET", "products.json", params=params).get("products", [])
    if not items:
        break
    for p in items:
        scanned += 1
        if (p["vendor"] or "").lower() != "bomibattery":
            skipped += 1
            continue
        try:
            c.request("PUT", f"products/{p['id']}.json",
                      json_body={"product": {"id": p["id"], "vendor": "Estry"}})
            changed += 1
            time.sleep(0.5)
        except Exception as e:
            failed += 1
            log(f"FAIL {p['id']}: {str(e)[:90]}")
    pid = items[-1]["id"]
    if scanned % 2500 < 250:
        rate = changed / max(time.time() - T0, 1)
        eta = max(15763 - changed, 0) / max(rate, 0.1) / 60
        log(f"scan={scanned} changed={changed} skip={skipped} fail={failed} "
            f"rate={rate:.2f}/s eta~{eta:.0f}min")
    if len(items) < 250:
        break

log(f"DONE scan={scanned} changed={changed} skip={skipped} fail={failed} "
    f"in {(time.time() - T0) / 60:.1f}min")
