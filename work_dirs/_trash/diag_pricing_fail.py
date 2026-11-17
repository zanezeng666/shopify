# -*- coding: utf-8 -*-
"""诊断 819 改价失败：抽 3 个待改价 pid 对账远端（存在性/status/id 一致性）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import db  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

eng = db.engine
client = StoreService().get_client(1)

# 待改价决策重算（dry）拿样例 pid
from shopify_admin.services.pricing import PricingService  # noqa: E402
svc = PricingService()
st = svc.run_all_stores(dry_run=True)
pids = []
for s in st["stores"]:
    if "recalc" in s:
        pids = s["recalc"].get("sample_pids") or []
        break

# 没有样例就从本地镜像拉价格差异对（简化：直接取 products 最近 3 个）
if not pids:
    with eng.connect() as c:
        rows = c.execute(text(
            "SELECT id, shopify_id, status, handle, price FROM products "
            "WHERE store_id=1 AND shopify_id IS NOT NULL ORDER BY id DESC LIMIT 3")).fetchall()
        pids = [r[1] for r in rows]
        print("mirror rows:", [(r[0], r[1], r[2], r[3], str(r[4])) for r in rows])

for pid in pids[:3]:
    try:
        r = client.graphql(
            "query($id:ID!){product(id:$id){id title status}}", {"id": f"gid://shopify/Product/{pid}"})
        print(pid, "->", str(r)[:150])
    except Exception as e:
        print(pid, "ERR", str(e)[:120])
