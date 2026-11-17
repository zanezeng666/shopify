# -*- coding: utf-8 -*-
"""重排终态复核（只读）：远端在架构成/三类残留/恢复抽查/镜像一致性。"""
import sys
import time
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import get_engine  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THREE = {"mobile, smartphone battery", "notebook, laptop battery",
         "camera battery"}

client = StoreService().get_client(1)
types, since, total = Counter(), 0, 0
while True:
    batch = client.request("GET", "products.json", params={
        "limit": 250, "status": "active", "since_id": since,
        "fields": "id,product_type"}).get("products", [])
    if not batch:
        break
    total += len(batch)
    for p in batch:
        types[(p.get("product_type") or "").strip()] += 1
    since = batch[-1]["id"]
    time.sleep(0.35)
client.close()
print(f"远端 ACTIVE 总数: {total}")
three_resid = {t: n for t, n in types.items() if t.lower() in THREE}
print(f"三类残留 ACTIVE: {three_resid or '无 ✓'}")
print("ACTIVE product_type TOP15:")
for t, n in types.most_common(15):
    print(f"  {t or '(空)':38} {n}")

with get_engine().connect() as m:
    r = m.execute(text(
        "SELECT status, COUNT(*) FROM products WHERE store_id=1 "
        "GROUP BY status")).fetchall()
    print(f"\n镜像状态分布: {dict(r)}")
    # 恢复抽查: rebalance_done 里 active 的 5 个
    done = [x.strip() for x in open("/tmp/rebalance_done.txt")]
    actives = [int(x.split(":")[1]) for x in done if x.startswith("active:")][:5]
    rows = m.execute(text(
        "SELECT shopify_product_id, status FROM products WHERE store_id=1 "
        "AND shopify_product_id IN :ids"),
        {"ids": tuple(actives)}).fetchall() if actives else []
    print(f"恢复品镜像抽查(前5): {rows}")
