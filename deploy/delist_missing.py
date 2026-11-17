# -*- coding: utf-8 -*-
"""下架 CS 已无供应的在线产品（先做）。

判定（产品级，防误伤：全部变体锚定的 csid 都不在 CS 在售集才下）：
  no_cs_record    —— cs_product 完全无该 cs_id 记录（orphans）
  cs_discontinued —— 有记录但该 cs_id 全部记录 status=0（停售）
  unanchored/混合在售 —— 不动
用法：
  dry-run:  python delist_missing.py
  试推 10:  python delist_missing.py 10
  全量:     nohup python delist_missing.py 0 > /tmp/delist.log 2>&1 &
断点 /tmp/delist_done.txt；错误 /tmp/delist_errors.log。
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from loguru import logger

from shopify_admin.services.products.sync_shopify import _CS_ID_RE
from shopify_admin.services.products.service import ProductService
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

logger.remove()
logger.add(sys.stderr, level="INFO")

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else -1   # -1 = dry-run
APPLY = LIMIT >= 0

svc = ProductService()
client = ShopifyRest(StoreService().get_client(1)).client

# CS 目录：csid → 有无任何记录 / 有无在售记录
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

catalog = CsShopifySyncService.load_cs_catalog()
cs_all: dict[str, bool] = {}      # csid -> exists
cs_alive: dict[str, bool] = {}    # csid -> any record on_sale
for (csid, _bl), row in catalog.items():
    cs_all[csid] = True
    if row["status"] == 1:
        cs_alive[csid] = True
logger.info(f"CS 目录 records={len(catalog)} unique_csids={len(cs_all)} alive={len(cs_alive)}")

Q = """
{
  products(first: 250, sortKey: CREATED_AT, query: "status:active") {
    pageInfo { hasNextPage endCursor }
    nodes { id title handle variants(first: 10) { nodes { sku } } }
  }
}"""

# ---- 阶段 1：全量拉取 + 判定 ----
to_delist: list[dict] = []
stat = dict(total=0, keep=0, unanchored_skip=0, no_cs_record=0, cs_discontinued=0)
cursor = None
pages = 0
t0 = time.monotonic()
while True:
    qq = Q.replace("(first: 250,", '(first: 250, after: "%s",' % cursor) if cursor else Q
    r = client.graphql(qq)
    pages += 1
    conn = r["products"]
    for p in conn["nodes"]:
        stat["total"] += 1
        csids = set()
        for v in p["variants"]["nodes"]:
            m = _CS_ID_RE.match((v["sku"] or "").strip())
            if m:
                csids.add(m.group(1))
        if not csids:
            stat["unanchored_skip"] += 1
            continue
        alive = [c for c in csids if cs_alive.get(c)]
        if alive:
            stat["keep"] += 1
            continue
        if any(c in cs_all for c in csids):
            reason = "cs_discontinued"
            stat["cs_discontinued"] += 1
        else:
            reason = "no_cs_record"
            stat["no_cs_record"] += 1
        to_delist.append({"pid": p["id"], "num": int(p["id"].rsplit("/", 1)[-1]),
                          "handle": p["handle"], "title": p["title"][:70],
                          "csids": sorted(csids)[:4], "reason": reason})
    cursor = conn["pageInfo"]["endCursor"]
    if not conn["pageInfo"]["hasNextPage"]:
        break
logger.info(f"拉取 {pages} 页 ({time.monotonic()-t0:.0f}s): {stat}")
logger.info(f"待下架 {len(to_delist)}：no_cs_record={stat['no_cs_record']} "
            f"cs_discontinued={stat['cs_discontinued']}")
for s in to_delist[:8]:
    logger.info(f"  样本 {s['reason']} {s['handle']} csids={s['csids']}")

if not APPLY:
    logger.info("dry-run 结束（不推送）。带参数运行即执行：10=试推，0=全量。")
    sys.exit(0)

# ---- 阶段 2：推送下架 ----
try:
    done = {int(x) for x in open("/tmp/delist_done.txt").read().split()}
except Exception:
    done = set()
tasks = [t for t in to_delist if t["num"] not in done]
if LIMIT:
    tasks = tasks[:LIMIT]
    logger.info(f"试推模式：截取 {len(tasks)} 个")

rest = ShopifyRest(StoreService().get_client(1))
ok_n = err_n = 0
consec = 0
df = open("/tmp/delist_done.txt", "a", encoding="utf-8")
ef = open("/tmp/delist_errors.log", "a", encoding="utf-8")
t1 = time.monotonic()
for i, tk in enumerate(tasks, 1):
    try:
        updated = rest.update_product(tk["num"], {"status": "draft"})
        if updated.get("id"):
            svc._upsert_product(1, updated)
            ok_n += 1
            consec = 0
            df.write(f"{tk['num']}\n")
        else:
            err_n += 1
            consec += 1
            ef.write(f"{tk['pid']} empty response\n")
    except Exception as e:  # noqa: BLE001
        err_n += 1
        consec += 1
        ef.write(f"{tk['pid']} {tk['handle']}: {str(e)[:200]}\n")
        if consec >= 20:
            logger.error(f"连续 {consec} 失败熔断（已推 {i-1}）")
            break
    if i % 50 == 0:
        df.flush()
        logger.info(f"下架 {i}/{len(tasks)} ok={ok_n} err={err_n}")
df.close()
ef.close()
logger.info(f"DONE ok={ok_n} err={err_n} 耗时 {time.monotonic()-t1:.0f}s")
