# -*- coding: utf-8 -*-
"""索引抢救 step2：执行 A 档收缩（1,447 个死重产品转 DRAFT）。

候选 = 无货(SZ/HK/US) ∧ 无亚马逊参考价 ∧ 非 medical ∧ 无历史销量（shrink_stats v3 档位A 补集）。
- 完全可逆：shopify_product_id 清单存档于 shrink_draft_ids.json，恢复只需 PUT status=active
- 写入节奏：0.45s 间隔（≤2.2/s 防 429），失败重试 3 次带退避
- 本地镜像 Product.status 同步置 draft
- 幂等可重跑：status 已为 draft 的 PUT 无副作用
"""
from __future__ import annotations

import json
import time

from sqlalchemy import update

from shopify_admin.core.database import session_scope
from shopify_admin.models.product import Product

IDS_FILE = "/home/jason/shopify-admin/deploy/shrink_draft_ids.json"
LOG_FILE = "/home/jason/shopify-admin/deploy/shrink_exec.log"


def log(msg: str) -> None:
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main() -> None:
    from shopify_admin.services.stores.service import StoreService

    with open(IDS_FILE, encoding="utf-8") as f:
        data = json.load(f)
    ids: list[int] = data["draftA"]
    log(f"A档候选 {len(ids)} 个开始转 DRAFT")

    client = StoreService().get_client(1)
    done: list[int] = []
    failed: list[int] = []
    try:
        for i, pid in enumerate(ids, 1):
            ok = False
            for attempt in range(3):
                try:
                    client.request(
                        "PUT", f"products/{pid}.json", json_body={"product": {"id": pid, "status": "draft"}}
                    )
                    ok = True
                    break
                except Exception as e:
                    if attempt == 2:
                        log(f"FAIL {pid}: {str(e)[:120]}")
                    else:
                        time.sleep(5 + attempt * 5)
            (done if ok else failed).append(pid)
            if i % 100 == 0 or i == len(ids):
                log(f"进度 {i}/{len(ids)} ok={len(done)} fail={len(failed)}")
            time.sleep(0.45)
    finally:
        client.close()

    # 本地镜像同步
    if done:
        with session_scope() as s:
            for j in range(0, len(done), 500):
                chunk = done[j:j + 500]
                s.execute(
                    update(Product)
                    .where(Product.store_id == 1, Product.shopify_product_id.in_(chunk))
                    .values(status="draft")
                )
    log(f"完成: ok={len(done)} fail={len(failed)} 本地镜像已同步; 失败清单: {failed[:20]}")


if __name__ == "__main__":
    main()
