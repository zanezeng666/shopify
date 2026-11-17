# -*- coding: utf-8 -*-
"""正式跑批：停售下架 + 全量改价（分轮限流收敛）。nohup 后台执行。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from loguru import logger

from shopify_admin.services.pricing import PricingService
from shopify_admin.services.stores.service import StoreService

logger.remove()
logger.add(sys.stderr, level="INFO")

svc = PricingService()
print("== build_decisions ==", flush=True)
decisions = svc.build_decisions()
priced = sum(1 for d in decisions.values() if d.price is not None)
print(f"decisions={len(decisions)} priced={priced}", flush=True)

stores = StoreService().list_stores(available_only=True)
report = {"started": time.strftime("%F %T"), "stores": []}

for st in stores:
    sid = st["id"]
    # 1) 停售下架
    print(f"\n== store{sid} delist ==", flush=True)
    dl = svc.delist_stopped(sid, decisions, dry_run=False)
    print(f"delist: {dl['delisted']}/{dl['to_delist']} failed={dl['failed']}", flush=True)
    if dl["errors"]:
        print("  errors:", *dl["errors"][:10], sep="\n   ", flush=True)

    # 2) 改价：GraphQL 批量（每产品一次 mutation），轮循环兜失败重试
    rnd, total_up, total_fail = 0, 0, 0
    stall = 0
    while rnd < 5:
        rnd += 1
        t0 = time.time()
        r = svc.recalc_store(sid, decisions, dry_run=False, use_graphql=True)
        total_up += r["updated"]
        total_fail += r["failed"]
        print(f"round{rnd} ({time.time()-t0:.0f}s): updated={r['updated']} "
              f"to_update={r['to_update']} failed={r['failed']} "
              f"unchanged={r['unchanged']}", flush=True)
        if r["errors"]:
            print("  errors:", *r["errors"][:6], sep="\n   ", flush=True)
        if r["to_update"] == 0:
            break
        if r["updated"] == 0:            # 无进展 → 防死循环
            stall += 1
            if stall >= 2:
                print("  stall 2 轮退出", flush=True)
                break
        else:
            stall = 0
    report["stores"].append({
        "store_id": sid, "delisted": dl["delisted"], "delist_failed": dl["failed"],
        "rounds": rnd, "updated": total_up, "failed": total_fail,
    })

report["finished"] = time.strftime("%F %T")
with open("/tmp/pricing_apply_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print("\nDONE", json.dumps(report["stores"], ensure_ascii=False), flush=True)
