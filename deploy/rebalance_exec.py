# -*- coding: utf-8 -*-
"""全店上架重排（新规则）。

规则（用户 2026-11-12 拍板）:
  DRAFT : ① product_type ∈ 三类(Mobile/Notebook/Camera) 全部在架品
          ② 其余在架品中 非(medical ∨ 近90天亚马逊出货) → 死库存下架
  ACTIVE: ③ 现 DRAFT 且 非三类 且 (medical ∨ 近90天出货) 且 全部csid在售且非停产
出货口径 = cs_bm.amazon_orders 近90天(取消单排除, FBA+MFN 都算)
用法: --plan 仅打印计划 | --go 执行(断点续跑, 0.45s/个, 失败重试3)
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text, update  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine, session_scope,
)
from shopify_admin.models.product import Product  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

THREE = {"mobile, smartphone battery", "notebook, laptop battery",
         "camera battery"}
DONE = "/tmp/rebalance_done.txt"
LOG = "/home/jason/shopify-admin/deploy/rebalance.log"


def log(msg):
    line = time.strftime("%H:%M:%S ") + str(msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def remote_ids(status):
    """远端实测某状态产品 id 全量(镜像 status 失真, 只信远端)。"""
    client = StoreService().get_client(1)
    ids, since = [], 0
    try:
        while True:
            batch = client.request("GET", "products.json", params={
                "limit": 250, "status": status, "since_id": since,
                "fields": "id"}).get("products", [])
            if not batch:
                break
            ids.extend(int(p["id"]) for p in batch)
            since = ids[-1]
            time.sleep(0.35)
    finally:
        client.close()
    return set(ids)


def build_plan():
    print("拉取远端 active/draft 产品清单...")
    remote_active = remote_ids("active")
    remote_draft = remote_ids("draft")
    print(f"远端实测: active={len(remote_active)} draft={len(remote_draft)}")
    with get_cs_engine().connect() as c:
        sold90 = {r[0].strip().upper() for r in c.execute(text("""
            SELECT DISTINCT cs_id FROM cs_bm.amazon_orders
            WHERE purchase_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
              AND (item_status IS NULL OR item_status <> 'Cancelled')
              AND cs_id IS NOT NULL AND cs_id <> ''
        """))}
        s2 = {r[0] for r in c.execute(text("""
            SELECT cs_id FROM cs_product_record p
            WHERE id = (SELECT id FROM cs_product_record q
                        WHERE q.cs_id = p.cs_id ORDER BY id DESC LIMIT 1)
              AND status IN ('Stop Production','Delete','Stop Limit In Stock')
        """))}
        dead = {r[0] for r in c.execute(text(
            "SELECT cs_id FROM cs_product GROUP BY cs_id "
            "HAVING SUM(status = 1) = 0"))}
        sample = [r[0] for r in c.execute(text(
            "SELECT DISTINCT cs_id FROM cs_bm.amazon_orders "
            "WHERE cs_id IS NOT NULL AND cs_id <> '' LIMIT 5"))]
    print(f"近90天出货csid={len(sold90)} 停产s2={len(s2)} 全停csid={len(dead)}")
    print(f"amazon_orders.cs_id 样例: {sample}")

    with get_engine().connect() as m:
        rows = m.execute(text(r"""
            SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid,
                   p.status, p.shopify_product_id, p.product_type, p.tags
            FROM product_variants pv
            JOIN products p ON p.id = pv.product_id
            WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
        """)).fetchall()
    prods: dict[int, dict] = {}
    for csid, st, spid, ptype, tags in rows:
        d = prods.setdefault(int(spid), dict(status=st, cs=set(),
                                             ptype=(ptype or "").strip(),
                                             tags=tags or ""))
        d["cs"].add(csid.strip().upper())
    n_unreach = sum(1 for d in prods.values() if not d["cs"])
    n_unreach_act = sum(1 for d in prods.values()
                        if not d["cs"] and d["status"] == "active")
    print(f"镜像产品={len(prods)} 无csid锚定={n_unreach}(在架{n_unreach_act},不动)")

    def three(d):
        return d["ptype"].lower() in THREE

    def med(d):
        return "ad-medical" in d["tags"] or "medical" in d["ptype"].lower()

    to_draft, to_active = [], []
    for spid, d in prods.items():
        if not d["cs"]:
            continue  # 非 CS 体系不动
        shipped = bool(d["cs"] & sold90)
        all_live = all(c not in s2 and c not in dead for c in d["cs"])
        if spid in remote_active:
            if three(d):
                to_draft.append((spid, "三类"))
            elif not (med(d) or shipped):
                to_draft.append((spid, "无出货非医疗"))
        elif spid in remote_draft:
            if not three(d) and (med(d) or shipped) and all_live:
                to_active.append(spid)
    return to_draft, to_active


def flip(client, ids, status, done_set):
    ok = fail = skip = 0
    for i, spid in enumerate(ids, 1):
        key = f"{status}:{spid}"
        if key in done_set:
            skip += 1
            continue
        good = False
        for attempt in range(3):
            try:
                client.request("PUT", f"products/{spid}.json", json_body={
                    "product": {"id": spid, "status": status}})
                good = True
                break
            except Exception as e:
                if attempt == 2:
                    log(f"FAIL {key}: {str(e)[:120]}")
                else:
                    time.sleep(5 + attempt * 5)
        if good:
            ok += 1
            with open(DONE, "a") as f:
                f.write(key + "\n")
        else:
            fail += 1
        if i % 100 == 0 or i == len(ids):
            log(f"{status} 进度 {i}/{len(ids)} ok={ok} fail={fail} skip={skip}")
        time.sleep(0.45)
    return ok, fail, skip


def sync_mirror(ids, status):
    if not ids:
        return
    with session_scope() as s:
        for j in range(0, len(ids), 500):
            s.execute(
                update(Product)
                .where(Product.store_id == 1,
                       Product.shopify_product_id.in_(ids[j:j + 500]))
                .values(status=status))


def main():
    mode = "--go" if "--go" in sys.argv else "--plan"
    to_draft, to_active = build_plan()
    n3 = sum(1 for _, w in to_draft if w == "三类")
    nd = len(to_draft) - n3
    print(f"\n计划: 三类→DRAFT {n3} | 死库存→DRAFT {nd} | 恢复→ACTIVE {len(to_active)}")
    if n3 + nd > 15000 or len(to_active) > 2000:
        print("!! 超护栏阈值, 终止(如确认请加 --force)")
        if "--force" not in sys.argv:
            return
    if mode == "--plan":
        print("(--plan 只读模式, 未执行任何写入)")
        return

    done_set = set()
    try:
        done_set = {x.strip() for x in open(DONE)} if __import__("os").path.exists(DONE) else set()
    except Exception:
        done_set = set()
    client = StoreService().get_client(1)
    try:
        log(f"== 开始: 三类+死库存→DRAFT {len(to_draft)} 个 ==")
        flip(client, [p for p, _ in to_draft], "draft", done_set)
        log(f"== 恢复→ACTIVE {len(to_active)} 个 ==")
        flip(client, to_active, "active", done_set)
    finally:
        client.close()
    sync_mirror([p for p, _ in to_draft], "draft")
    sync_mirror(to_active, "active")
    log("镜像已同步, 重排完成")


if __name__ == "__main__":
    main()
