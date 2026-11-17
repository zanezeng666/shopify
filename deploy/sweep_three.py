# -*- coding: utf-8 -*-
"""三类残留补刀：以远端 product_type 为权威口径清一遍(幂等)。"""
import sys
import time
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import update  # noqa: E402
from shopify_admin.core.database import session_scope  # noqa: E402
from shopify_admin.models.product import Product  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THREE = {"mobile, smartphone battery", "notebook, laptop battery",
         "camera battery"}

client = StoreService().get_client(1)
victims, since = [], 0
types = Counter()
while True:
    batch = client.request("GET", "products.json", params={
        "limit": 250, "status": "active", "since_id": since,
        "fields": "id,product_type"}).get("products", [])
    if not batch:
        break
    for p in batch:
        t = (p.get("product_type") or "").strip()
        types[t] += 1
        if t.lower() in THREE:
            victims.append((int(p["id"]), t))
    since = batch[-1]["id"]
    time.sleep(0.35)

print(f"远端 ACTIVE 总数 {sum(types.values())} | 三类残留 {len(victims)}")
ok = fail = 0
for pid, t in victims:
    try:
        client.request("PUT", f"products/{pid}.json",
                       json_body={"product": {"id": pid, "status": "draft"}})
        ok += 1
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"FAIL {pid} {t}: {str(e)[:100]}")
    time.sleep(0.45)
print(f"补刀转 draft: ok={ok} fail={fail}")
client.close()
if victims:
    ids = [p for p, _ in victims]
    with session_scope() as s:
        for j in range(0, len(ids), 500):
            s.execute(update(Product)
                      .where(Product.store_id == 1,
                             Product.shopify_product_id.in_(ids[j:j + 500]))
                      .values(status="draft"))
    print("镜像已同步")
