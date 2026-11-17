# -*- coding: utf-8 -*-
"""补建新品（2026-11-12 新规则版 launch_new）。

判据（用户拍板）:
  引擎 to_create（CS在售∧电池∧无镜像，已排除手机/相机/笔记本三类）
  ∧ (CS类目含 medical ∨ cs_bm.amazon_orders 近90天有出货)
  ∧ 三仓(SZ/HK/US)有库存（与 CsChannel.get_inventory 同源）
用法: dry-run=无参数 | 试推 N | 全量 0
断点 /tmp/relaunch_done.txt；错误 /tmp/relaunch_errors.log
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
comp = svc._compute(1, "report")
creates = comp["to_create"]

with get_cs_engine().connect() as conn:
    sold90 = {r[0].strip().upper() for r in conn.execute(text("""
        SELECT DISTINCT cs_id FROM cs_bm.amazon_orders
        WHERE purchase_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
          AND (item_status IS NULL OR item_status <> 'Cancelled')
          AND cs_id IS NOT NULL AND cs_id <> ''
    """)).all()}
    inv3 = {r[0].strip().upper() for r in conn.execute(text(
        "SELECT DISTINCT cs_id FROM cs_inventory "
        "WHERE location IN ('US','SZ','HK') AND quantity > 0")).all()}
    med_cats = {r[0] for r in conn.execute(text(
        "SELECT DISTINCT cs_id FROM cs_product "
        "WHERE LOWER(category) LIKE '%medical%'")).all()}

have = [i for i in creates
        if i["cs_id"].strip().upper() in inv3
        and (i["cs_id"].strip().upper() in sold90
             or i["cs_id"].strip().upper() in med_cats)]
logger.info(f"to_create={len(creates)} 符合新规(出货∨医疗)∧三仓有货={len(have)} "
            f"[其中医疗类目 {sum(1 for i in have if i['cs_id'] in med_cats)}]")

try:
    done = {x.strip() for x in
            open("/tmp/relaunch_done.txt").read().split() if x.strip()}
except Exception:
    done = set()
tasks = [i for i in have if i["cs_id"] not in done]
logger.info(f"断点后待建 {len(tasks)}")

if not APPLY:
    for s in tasks[:5]:
        tag = "医疗" if s["cs_id"] in med_cats else "出货"
        logger.info(f"  样本 {s['cs_id']}/{s.get('brand')} [{tag}] "
                    f"handle={s['payload'].get('handle', '')[:60]}")
    logger.info("dry-run 结束。带参数执行：10=试推，0=全量。")
    sys.exit(0)

if LIMIT:
    tasks = tasks[:LIMIT]
    logger.info(f"试推模式：截取 {len(tasks)}")

client = StoreService().get_client(1)
rest = ShopifyRest(client)
img_http = httpx.Client(timeout=10, follow_redirects=True, headers=_CS_IMG_HEADERS)
stat = dict(created=0, skipped_existing=0, failed=0,
            images_attached=0, images_missing=0)
consec = 0
WORKERS = 4
lock = __import__("threading").Lock()
stop = False


def build(item):
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

df = open("/tmp/relaunch_done.txt", "a", encoding="utf-8")
ef = open("/tmp/relaunch_errors.log", "a", encoding="utf-8")
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
                    ef.write(f"create {item['cs_id']}/{item.get('brand')}: "
                             f"{str(e)[:180]}\n")
                    if consec >= 20:
                        logger.error(f"连续 {consec} 失败熔断")
                        stop = True
                        for f2 in futs:
                            f2.cancel()
            if n % 50 == 0:
                df.flush()
                rate = n / max(time.monotonic() - t0, 1)
                eta = (len(tasks) - n) / max(rate, 0.1) / 60
                logger.info(f"建品 {n}/{len(tasks)} (ETA {eta:.0f}m) {stat}")
finally:
    df.close()
    ef.close()
    img_http.close()
    client.close()
logger.info(f"DONE {stat} 耗时 {(time.monotonic()-t0)/60:.1f}m")
