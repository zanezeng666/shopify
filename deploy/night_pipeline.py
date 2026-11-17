# -*- coding: utf-8 -*-
"""夜间编排：等全量刷新结束 -> Camera 产品转 DRAFT -> 复核 -> 抽验 -> 报告。
nohup 挂服务器执行，产物 deploy/night_report.txt
"""
import subprocess
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

REPORT = "/home/jason/shopify-admin/deploy/night_report.txt"
LOG = "/home/jason/shopify-admin/deploy/refresh_all.log"
out_lines = []


def log(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    print(line, flush=True)
    out_lines.append(line)


def dump():
    with open(REPORT, "w") as f:
        f.write("\n".join(out_lines) + "\n")


# ---- 1) 等全量刷新进程退出（上限 4h） ----
log("== 1) 等待全量刷新结束 ==")
deadline = time.time() + 4 * 3600
while time.time() < deadline:
    r = subprocess.run("pgrep -f refresh_all_v22 | wc -l",
                       shell=True, capture_output=True, text=True)
    if r.stdout.strip() == "0":
        log("刷新进程已退出")
        break
    time.sleep(120)
else:
    log("超时 4h，放弃等待")
tail = subprocess.run(f"tail -5 {LOG}", shell=True,
                      capture_output=True, text=True).stdout
log("刷新日志尾部:\n" + tail)
dump()

# ---- 2) Camera 产品转 DRAFT ----
log("== 2) Camera Battery ACTIVE -> DRAFT ==")
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
log(f"转 DRAFT 完成: {done} 成功 / {fail} 失败")
dump()

# ---- 3) 复核分类状态 ----
log("== 3) 分类 ACTIVE 复核 ==")
r = subprocess.run(
    ".venv/bin/python deploy/check_nav_type_status.py",
    shell=True, capture_output=True, text=True,
    cwd="/home/jason/shopify-admin")
log(r.stdout.strip())
dump()

# ---- 4) 刷新效果抽验 ----
log("== 4) 刷新抽验 ==")
r = subprocess.run(
    ".venv/bin/python deploy/verify_refresh_sample.py",
    shell=True, capture_output=True, text=True,
    cwd="/home/jason/shopify-admin")
log(r.stdout.strip()[-2000:])
log("== 夜间编排全部完成 ==")
dump()
