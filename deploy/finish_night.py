# -*- coding: utf-8 -*-
"""收尾：Camera 转 DRAFT -> 分类复核 -> 刷新抽验 -> 报告。"""
import subprocess
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

REPORT = "/home/jason/shopify-admin/deploy/night_report.txt"
out_lines = []


def log(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    print(line, flush=True)
    out_lines.append(line)


def dump():
    with open(REPORT, "w") as f:
        f.write("\n".join(out_lines) + "\n")


log("== 1) Camera Battery ACTIVE -> DRAFT ==")
cl = ShopifyRest(StoreService().get_client(1)).client
q = """query($after: String) {
  products(first: 100, after: $after,
           query: "product_type:'Camera Battery' AND status:active") {
    nodes { id title }
    pageInfo { hasNextPage endCursor }
  }
}"""
mu = """mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product { id status }
    userErrors { field message }
  }
}"""
done = fail = 0
cursor = None
while True:
    d = cl.graphql(q, {"after": cursor}).get("products", {})
    for p in d.get("nodes", []):
        r = cl.graphql(mu, {"input": {"id": p["id"], "status": "DRAFT"}})
        ue = r.get("productUpdate", {}).get("userErrors") or []
        if ue:
            fail += 1
            log(f"  FAIL {p['title'][:40]}: {ue}")
        else:
            done += 1
    if not d.get("pageInfo", {}).get("hasNextPage"):
        break
    cursor = d["pageInfo"]["endCursor"]
log(f"转 DRAFT: {done} 成功 / {fail} 失败")
dump()

log("== 2) 分类 ACTIVE 复核 ==")
r = subprocess.run(
    ".venv/bin/python deploy/check_nav_type_status.py",
    shell=True, capture_output=True, text=True,
    cwd="/home/jason/shopify-admin")
log(r.stdout.strip())
dump()

log("== 3) 刷新抽验 ==")
r = subprocess.run(
    ".venv/bin/python deploy/verify_refresh_sample.py",
    shell=True, capture_output=True, text=True,
    cwd="/home/jason/shopify-admin")
log(r.stdout.strip()[-1500:])
log("== 收尾完成 ==")
dump()
