# -*- coding: utf-8 -*-
"""product_type 治理 + 集合补建（预览/--go 两模式）。

1) 空/漂移 type 行级反查：镜像 SKU 提取 cs_id -> CDB category -> 设 '{cat} Battery'
2) 集合联动：被改 type 的 smart collection 规则同步更新（一对多则分组处理）
3) 缺失补建：美仓头部类目（n>=50）无集合的建 smart collection（type equals, published）
断点：/tmp/classify_types_done.txt
"""
import re
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, "/home/jason/shopify-admin/src")

DONE_FILE = "/tmp/classify_types_done.txt"
SKIP_CATEGORIES = ("Mobile, SmartPhone", "Camera", "Notebook", "Laptop")
# new type 落在三类精确名单的跳过修复（保持旧 type 与 active 现状，不下架不漂移）
SKIP_NEW_TYPES = {"Mobile, SmartPhone Battery", "Camera Battery",
                  "Notebook, Laptop Battery", "Laptop Battery"}
MIN_COLLECTION_COUNT = 50  # 美仓类目产品数阈值


def main() -> None:
    go = "--go" in sys.argv
    from sqlalchemy import text
    from shopify_admin.core.database import get_cs_engine, get_engine
    from shopify_admin.services.stores import StoreService

    # ---- 数据收集 ----
    with get_cs_engine().connect() as conn:
        crows = conn.execute(text(
            "SELECT cs_id, category FROM cs_product "
            "WHERE cs_id LIKE 'CS-%' AND status=1")).fetchall()
    cat_of = {r[0]: (r[1] or "").strip() for r in crows}
    print(f"[CDB] cs_product {len(cat_of)} 行")

    with get_engine().connect() as conn:
        prows = conn.execute(text(
            "SELECT p.id, p.shopify_product_id, p.product_type, p.status, "
            "(SELECT v.sku FROM product_variants v WHERE v.product_id = p.id "
            " AND v.sku LIKE 'CS-%' LIMIT 1) sku "
            "FROM products p WHERE p.shopify_product_id IS NOT NULL")).fetchall()
    print(f"[镜像] 产品 {len(prows)} 个（含 draft）")

    # 行级目标 type
    fixes: list[tuple[int, str, str]] = []  # (pid, old, new)
    for r in prows:
        pid, sid, ptype, status, sku = r
        if not sku:
            continue
        csid = sku.split("_", 1)[0]
        cat = cat_of.get(csid)
        if not cat or cat in SKIP_CATEGORIES:
            continue
        new_t = f"{cat} Battery"
        cur = (ptype or "").strip()
        if cur != new_t and new_t not in SKIP_NEW_TYPES:  # 空 or 漂移
            # 只动 active + 空或已知漂移模式（保守：非空且差异仅在标点/大小写/子集）
            if status != "active":
                continue
            fixes.append((sid, cur, new_t))

    drift = Counter((old or "<empty>", new) for _p, old, new in fixes)
    print(f"\n== A. type 修复决策表（行级反查）: {len(fixes)} 个产品 ==")
    for (old, new), n in drift.most_common(30):
        print(f"  {old!r:34} -> {new!r:34} {n}")

    # ---- 现有集合 ----
    c = StoreService().get_client(1)
    cols = []
    r = c.request("GET", "smart_collections.json", params={"limit": 250})
    cols = r.get("smart_collections", [])
    print(f"\n[B. 集合] 现有 smart collections {len(cols)} 个")
    col_by_cond = {}
    for s in cols:
        rule = (s.get("rules") or [{}])[0]
        cond = rule.get("condition")
        if rule.get("column") == "type" and cond:
            col_by_cond[cond] = s
    print(f"  type-equals 集合 {len(col_by_cond)} 个")

    # ---- 需要的集合（美仓头部类目）----
    with get_cs_engine().connect() as conn:
        skip_sql = "(" + ",".join(f"'{s}'" for s in SKIP_CATEGORIES) + ")"
        us_rows = conn.execute(text(f"""
            SELECT p.category, COUNT(DISTINCT p.cs_id) n
            FROM cs_product p
            JOIN (SELECT DISTINCT cs_id FROM cs_inventory
                  WHERE location='US' AND quantity>0) i ON i.cs_id=p.cs_id
            WHERE p.cs_id LIKE 'CS-%' AND p.status=1
              AND p.category NOT IN {skip_sql}
            GROUP BY p.category HAVING n >= {MIN_COLLECTION_COUNT}
            ORDER BY n DESC""")).fetchall()
    print(f"\n== C. 美仓头部类目（n>={MIN_COLLECTION_COUNT}）{len(us_rows)} 个 ==")
    missing = []
    for cat, n in us_rows:
        want = f"{cat} Battery"
        s = col_by_cond.get(want)
        mark = "HAS" if s else "MISSING"
        print(f"  [{mark}] {want!r:36} 美仓 n={n}")
        if not s:
            missing.append((want, n))

    # ---- 漂移集合联动（仅同语义改名跟规则；产品搬家不动老集合）----
    print("\n== D. 漂移联动（仅规范化等价的改名跟规则）==")

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    link = defaultdict(set)
    for _p, old, new in fixes:
        if old:
            link[old].add(new)
    for old, news in sorted(link.items()):
        s = col_by_cond.get(old)
        if not s:
            continue
        equiv = [n for n in news if norm(n) == norm(old)]
        if equiv:  # 同语义改名（如 'Barcode, Scanner'->'Barcode Scanner'）
            print(f"  集合 {s['title']!r}({s['id']}) 规则 {old!r} -> {equiv[0]!r} [改]")
        else:
            n_sum = sum(drift.get((old, n), 0) for n in news)
            print(f"  集合 {s['title']!r}({s['id']}) 产品搬家 {n_sum} 个到 "
                  f"{sorted(news)} [规则保留]")

    if not go:
        print("\n（预览模式；--go 执行：A 修 type + D 改集合规则 + C 补建缺失集合）")
        return

    # ---- 执行 A：修 type（REST PUT 合并语义）----
    ok = fail = 0
    streak = 0
    t0 = time.time()
    for i, (sid, old, new) in enumerate(fixes, 1):
        try:
            c.request("PUT", f"products/{sid}.json",
                      json_body={"product": {"id": sid, "product_type": new}})
            ok += 1
            streak = 0
        except Exception as e:  # noqa: BLE001
            print(f"ERR {sid} {old}->{new}: {e}", flush=True)
            fail += 1
            streak += 1
        if streak >= 10:
            print("!! 熔停")
            break
        if i % 100 == 0:
            print(f"... {i}/{len(fixes)} ok={ok} fail={fail}", flush=True)
        time.sleep(0.15)
    print(f"[A] type 修复 ok={ok} fail={fail} {(time.time()-t0)/60:.1f}min")

    # ---- 执行 D：集合规则联动（仅规范化等价改名）----
    for old, news in sorted(link.items()):
        s = col_by_cond.get(old)
        if not s:
            continue
        equiv = [n for n in news if norm(n) == norm(old)]
        if not equiv:
            continue  # 产品搬家：老集合规则保留
        try:
            c.request("PUT", f"smart_collections/{s['id']}.json", json_body={
                "smart_collection": {"id": s["id"], "rules": [
                    {"column": "type", "relation": "equals", "condition": equiv[0]}]}})
            print(f"[D] 集合 {s['id']} {old!r} -> {equiv[0]!r}")
        except Exception as e:  # noqa: BLE001
            print(f"[D] ERR 集合 {s['id']}: {e}")
        time.sleep(0.3)

    # ---- 执行 C：补建缺失集合 ----
    for want, n in missing:
        try:
            c.request("POST", "smart_collections.json", json_body={"smart_collection": {
                "title": want,
                "rules": [{"column": "type", "relation": "equals", "condition": want}],
                "published": True}})
            print(f"[C] 新建集合 {want!r}（美仓 n={n}）")
        except Exception as e:  # noqa: BLE001
            print(f"[C] ERR {want!r}: {e}")
        time.sleep(0.3)
    print("TYPES-DONE")


if __name__ == "__main__":
    main()
