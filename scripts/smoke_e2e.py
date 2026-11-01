# -*- coding: utf-8 -*-
"""端到端冒烟（安全链路，不产生真实渠道订单）：

1. 拉单       真实 Shopify API，增量游标，1 页
2. 分仓       route_order(dry_run=True)：真实渠道库存查询，不写库
3. 渠道只读   CS 本地镜像库存 + FastRite 真实 API 库存
4. 轮询回传   poll_channel_status（当前无在途单 → 空结果路径）
5. REST       TestClient：/stores、/tasks/jobs、POST /tasks/daily_report/run、审计落库
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import func, select

from shopify_admin.channels.registry import get_channel
from shopify_admin.core.database import session_scope
from shopify_admin.models.order import Order, OrderItem
from shopify_admin.services.fulfillment.service import FulfillmentService
from shopify_admin.services.orders.service import OrderService

STORE_ID = 1

# ------------------------------------------------------------------ 1. 拉单
r = OrderService().sync_orders(store_id=STORE_ID, max_pages=1)
print(f"[1] 拉单 fetched={r.fetched} created={r.created} updated={r.updated}")

# ------------------------------------------------- 2. 选单 dry_run 分仓（不写库）
target = None
with session_scope() as s:
    ids = [
        row[0] for row in s.execute(
            select(Order.id)
            .where(Order.store_id == STORE_ID, Order.raw.isnot(None))
            .order_by(Order.id.desc())
            .limit(30)
        )
    ]
for oid in ids:
    with session_scope() as s:
        n = s.execute(
            select(func.count(OrderItem.id)).where(
                OrderItem.order_id == oid, OrderItem.sku != ""
            )
        ).scalar()
    if n:
        target = oid
        break
assert target, "无可路由订单（同步后应有带 SKU 行项的订单）"

svc = FulfillmentService()
dec = svc.route_order(target, dry_run=True)
print(f"[2] dry_run 分仓 order={target}:")
for d in dec["decisions"]:
    print(f"    {d['sku'][:44]:44s} -> {d['channel']:8s} ({d['reason']})")

# ------------------------------------------------------------------ 3. 渠道只读
sku = next(d["sku"] for d in dec["decisions"] if d["sku"])
ci = get_channel("cs").get_inventory(sku)
print(f"[3a] CS 镜像库存 {sku[:40]} -> cs_id={ci.cs_id} available={ci.available}")
fr = get_channel("fastrite").get_inventory(sku)
print(f"[3b] FastRite API 库存 {sku[:40]} -> available={fr.available}")

# ------------------------------------------------------------------ 4. 轮询回传
p = svc.poll_channel_status()
print(f"[4] 渠道轮询: {p}")

# ------------------------------------------------------------------ 5. REST 手动触发 + 审计
from fastapi.testclient import TestClient

from shopify_admin.api.app import create_app

with TestClient(create_app()) as client:
    rsp = client.get("/stores")
    assert rsp.status_code == 200 and rsp.json()["items"], rsp.text
    print(f"[5] GET /stores -> {len(rsp.json()['items'])} 店铺")

    rsp = client.get("/tasks/jobs")
    jobs = rsp.json()["jobs"]
    assert rsp.status_code == 200 and len(jobs) == 5, rsp.text
    print(f"[6] GET /tasks/jobs -> {[j['name'] for j in jobs]}")

    rsp = client.post("/tasks/daily_report/run")
    assert rsp.status_code == 200, rsp.text
    print(f"[7] POST /tasks/daily_report/run -> {rsp.json()['result']}")

    rsp = client.get("/tasks", params={"limit": 10})
    items = [
        it for it in rsp.json().get("items", [])
        if "daily_report" in (it.get("task_name") or "")
    ]
    assert items, "审计记录未落库"
    top = items[0]
    assert top["success"], top
    print(f"[8] 审计落库 -> {top['task_name']} success={top['success']} ({top['duration_s']}s)")

print("SMOKE PASS")
