"""诊断：scheduler 配置与最近任务记录（甄别订单拉取/库存同步是否在跑）。"""
import os
import re

import pymysql

ENV = "/home/jason/shopify-admin/.env"
env = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            env[m.group(1)] = m.group(2)

print("== SCHEDULER 配置 ==")
for k in sorted(env):
    if k.startswith("SCHEDULER_"):
        print(f"{k}={env[k]}")

c = pymysql.connect(
    host=env["SHOPIFY_DB_HOST"], port=int(env.get("SHOPIFY_DB_PORT", "3306")),
    user=env["SHOPIFY_DB_USER"], password=env["SHOPIFY_DB_PASSWORD"],
    database=env["SHOPIFY_DB_NAME"], charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)
cur = c.cursor()

print("\n== task_result 结构与最近 8 条 ==")
cur.execute("SHOW COLUMNS FROM task_result")
print("cols:", [x["Field"] for x in cur.fetchall()])
cur.execute("SELECT * FROM task_result ORDER BY id DESC LIMIT 8")
for r in cur.fetchall():
    print(r)

print("\n== inventory_sync_logs 最近 5 条 ==")
cur.execute("SHOW COLUMNS FROM inventory_sync_logs")
cols = [x["Field"] for x in cur.fetchall()]
print("cols:", cols)
sel = ", ".join(cols)
cur.execute(f"SELECT {sel} FROM inventory_sync_logs ORDER BY id DESC LIMIT 5")
for r in cur.fetchall():
    print(r)

print("\n== orders 最近 3 条（时间字段）==")
cur.execute("SHOW COLUMNS FROM orders")
ocols = [x["Field"] for x in cur.fetchall()]
pick = [x for x in ("id", "order_no", "created_at", "financial_status", "total_price") if x in ocols]
cur.execute(f"SELECT {', '.join(pick)} FROM orders ORDER BY id DESC LIMIT 3")
for r in cur.fetchall():
    print(r)
c.close()
