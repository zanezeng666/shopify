# -*- coding: utf-8 -*-
"""上架 CS 新品（有库存才上）。

过滤：cs_inventory 按仓聚合 SUM(quantity) > 0（与 CsChannel.get_inventory 同源同口径）。
建品：复用 sync_shopify 建品链路——handle 查重幂等 + cameronsino 图外链探测
      + REST create + 镜像回写，status=active。
用法：
  dry-run:  python launch_new.py
  试推 10:  python launch_new.py 10
  全量:     nohup python launch_new.py 0 > /tmp/launch.log 2>&1 &
断点 /tmp/launch_done.txt（cs_id，含 skipped_existing）；错误 /tmp/launch_errors.log。
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
import httpx
from loguru import logger
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine
from shopify_admin.services.products.sync_shopify import (
    CsShopifySyncService, _CS_IMG_HEADERS)
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

logger.remove()
logger.add(sys.stderr, level="INFO")

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else -1   # -1 = dry-run
APPLY = LIMIT >= 0

svc = CsShopifySyncService()
c = svc._compute(1, "report")
creates = c["to_create"]

with get_cs_engine().connect() as conn:
    inv = {r[0]: int(r[1] or 0) for r in conn.execute(
        text("SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id")).all()}
have = [i for i in creates if inv.get(i["cs_id"], 0) > 0]
no_stock = len(creates) - len(have)
logger.info(f"to_create={len(creates)} 有库存={len(have)} 无库存跳过={no_stock}")

try:
    done = {x.strip() for x in open("/tmp/launch_done.txt").read().split() if x.strip()}
except Exception:
    done = set()
tasks = [i for i in have if i["cs_id"] not in done]
logger.info(f"断点后待建 {len(tasks)}")

if not APPLY:
    for s in tasks[:5]:
        logger.info(f"  样本 {s['cs_id']}/{s.get('brand')} qty={inv.get(s['cs_id'])} "
                    f"handle={s['payload'].get('handle', '')[:60]}")
    logger.info("dry-run 结束（不建品）。带参数运行即执行：10=试推，0=全量。")
    sys.exit(0)

if LIMIT:
    tasks = tasks[:LIMIT]
    logger.info(f"试推模式：截取 {len(tasks)}")

client = svc._stores.get_client(1)
rest = ShopifyRest(client)
img_http = httpx.Client(timeout=10, follow_redirects=True, headers=_CS_IMG_HEADERS)
stat = dict(created=0, skipped_existing=0, failed=0, images_attached=0, images_missing=0)
errors: list[str] = []
consec = 0
WORKERS = 4
lock = __import__("threading").Lock()
stop = False


def build(item: dict) -> tuple[str, str]:
    """返回 (结果, 详情)：ok/skip/fail。幂等：handle 已存在即补镜像跳过。"""
    cs_id = item["cs_id"]
    existing = rest.product_by_handle(item["payload"]["handle"])
    if existing:
        svc._products._upsert_product(1, existing)
        return "skip", cs_id
    payload = dict(item["payload"])
    payload["status"] = "active"
    urls = svc._probe_images(cs_id, img_http)
    if urls:
        payload["images"] = [{"src": u} for u in urls]
    created = rest.create_product(payload)
    svc._products._upsert_product(1, created)
    return "ok", cs_id + ("|img" if urls else "|noimg")


from concurrent.futures import ThreadPoolExecutor, as_completed

df = open("/tmp/launch_done.txt", "a", encoding="utf-8")
ef = open("/tmp/launch_errors.log", "a", encoding="utf-8")
t0 = time.monotonic()
try:
    with ThreadPoolExecutor(WORKERS) as ex:
        futs = {}
        for it in tasks:
            if stop:
                break
            futs[ex.submit(build, it)] = it
        for n, fut in enumerate(as_completed(futs), 1):
            item = futs[fut]
            try:
                kind, info = fut.result()
                with lock:
                    if kind == "ok":
                        stat["created"] += 1
                        if info.endswith("|noimg"):
                            stat["images_missing"] += 1
                        else:
                            stat["images_attached"] += 1
                    elif kind == "skip":
                        stat["skipped_existing"] += 1
                    df.write(item["cs_id"] + "\n")
                    consec = 0
            except Exception as e:  # noqa: BLE001
                with lock:
                    stat["failed"] += 1
                    consec += 1
                    msg = f"create {item['cs_id']}/{item.get('brand')}: {str(e)[:180]}"
                    errors.append(msg)
                    ef.write(msg + "\n")
                    if consec >= 30:
                        logger.error(f"连续 {consec} 失败熔断（已处理 {n-1}）")
                        stop = True
                        for f2 in futs:
                            f2.cancel()
            if n % 100 == 0:
                df.flush()
                rate = n / max(time.monotonic() - t0, 1)
                eta = (len(tasks) - n) / max(rate, 0.1) / 60
                logger.info(f"建品 {n}/{len(tasks)} ({rate:.2f}/s ETA {eta:.0f}m) "
                            f"ok={stat['created']} skip={stat['skipped_existing']} err={stat['failed']}")
finally:
    df.close()
    ef.close()
    img_http.close()
    client.close()
logger.info(f"DONE {stat} 耗时 {(time.monotonic()-t0)/60:.1f}m")
