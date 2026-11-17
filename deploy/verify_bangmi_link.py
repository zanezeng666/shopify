"""切换后验证：BMAI 对接 + 拉单实跑 + task_result。jason 环境跑。"""
import os
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

ENV = "/home/jason/shopify-admin/.env"
env = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
        if m:
            env[m.group(1)] = m.group(2)
os.environ.update(env)

import httpx  # noqa: E402
import pymysql  # noqa: E402

print("== A) BMAI cs-api ship-method（CS_API_KEY 实证）==")
key = env.get("CS_API_KEY", "")
r = httpx.get(
    "http://127.0.0.1:8001/v1/fulfillment/ship-method",
    params={"country_code": "US"},
    headers={"X-API-Key": key},
    timeout=15,
)
print("status:", r.status_code, "body:", r.text[:200])

print("\n== B) 手动触发一次拉单（job_pull_orders 真跑）==")
from shopify_admin.scheduler.jobs import job_pull_orders  # noqa: E402

print("result:", job_pull_orders())

print("\n== C) task_result 最新 3 条 ==")
c = pymysql.connect(
    host=env["SHOPIFY_DB_HOST"], port=int(env.get("SHOPIFY_DB_PORT", "3306")),
    user=env["SHOPIFY_DB_USER"], password=env["SHOPIFY_DB_PASSWORD"],
    database=env["SHOPIFY_DB_NAME"], charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)
cur = c.cursor()
cur.execute(
    "SELECT id, task_name, result, error, started_at FROM task_result ORDER BY id DESC LIMIT 3"
)
for row in cur.fetchall():
    print(row)
c.close()
