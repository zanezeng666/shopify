# -*- coding: utf-8 -*-
"""三类电池（手机/相机/笔记本）批量转 draft 下架。

用法：
  python archive_three.py                 # 只读预览：各 type 计数
  python archive_three.py --go            # 全量下架（断点续跑）
  python archive_three.py --go --limit 100# 小批 100 个验证
  python archive_three.py --restore       # 把断点文件记录的全部恢复 ACTIVE
断点：/tmp/classify_archive_done.txt（gid 列表，幂等续跑）
"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

DONE_FILE = "/tmp/classify_archive_done.txt"
# 类目前缀（product_type = '{category} Battery'）
TYPE_PREFIXES = ("Mobile", "Camera", "Notebook", "Laptop", "Tablet PC")
# 注：Tablet PC 归平板，不在三类之列，仅列出核对用，默认不启用

ACTIVE_PREFIXES = ("Mobile", "Camera", "Notebook", "Laptop")

# 精确下架名单（热成像/安防/移动传真等专业设备电池保留）
ARCHIVE_TYPES = ["Notebook, Laptop Battery", "Mobile, SmartPhone Battery",
                 "Camera Battery"]

UPD_MUT = """
mutation PUpd($product: ProductUpdateInput!) {
  productUpdate(product: $product) {
    product { id status }
    userErrors { field message }
  }
}
"""


def fetch_ids(c, ptype: str) -> list[int]:
    """镜像库直查（query 语法对含逗号 type 失效，镜像即权威全量）。"""
    from sqlalchemy import text as _t
    from shopify_admin.core.database import get_engine
    with get_engine().connect() as conn:
        rows = conn.execute(_t(
            "SELECT shopify_product_id FROM products "
            "WHERE status='active' AND product_type=:t "
            "AND shopify_product_id IS NOT NULL"),
            {"t": ptype}).fetchall()
    return sorted(int(r[0]) for r in rows)


def load_done() -> set[str]:
    try:
        with open(DONE_FILE) as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()


def append_done(gid: str) -> None:
    with open(DONE_FILE, "a") as f:
        f.write(gid + "\n")


def main() -> None:
    go = "--go" in sys.argv
    restore = "--restore" in sys.argv
    limit = 0
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    done = load_done()
    print(f"断点记录: {len(done)} 个已完成 gid")

    if restore:
        gids = sorted(done)
        print(f"== 恢复 {len(gids)} 个产品为 ACTIVE ==")
        ok = fail = 0
        for i, gid in enumerate(gids, 1):
            try:
                r = c.graphql(UPD_MUT, {"product": {"id": gid, "status": "ACTIVE"}})
                errs = (r.get("productUpdate") or {}).get("userErrors") or []
                if errs:
                    print(f"  ERR {gid}: {errs}")
                    fail += 1
                else:
                    ok += 1
            except Exception as e:  # noqa: BLE001
                print(f"  EXC {gid}: {e}")
                fail += 1
            if i % 100 == 0:
                print(f"  ... {i}/{len(gids)} ok={ok} fail={fail}")
            time.sleep(0.1)
        print(f"RESTORE-DONE ok={ok} fail={fail}（断点文件保留，确认无误后可删除）")
        return

    # ---- 预览：镜像库先核实三类真实 type 名 ----
    from sqlalchemy import text as _text
    from shopify_admin.core.database import get_engine
    with get_engine().connect() as conn:
        trows = conn.execute(_text(
            "SELECT product_type, COUNT(*) n FROM products "
            "WHERE status='active' AND (product_type LIKE '%obile%' "
            "OR product_type LIKE '%amera%' OR product_type LIKE '%otebook%' "
            "OR product_type LIKE '%aptop%') "
            "GROUP BY product_type ORDER BY n DESC")).fetchall()
    print("== 镜像相关 type 分布 ==")
    type_counts = {}
    for t in trows:
        print(f"  {t[0]!r:36} active={t[1]}")
        type_counts[t[0]] = t[1]
    candidates = {pt: None for pt in ARCHIVE_TYPES if pt in type_counts}
    missing = [pt for pt in ARCHIVE_TYPES if pt not in type_counts]
    if missing:
        print(f"  !! 名单中未命中: {missing}")
    if not candidates:
        print("NO-CANDIDATES（检查 type 名）")
        return

    total = 0
    for pt in list(candidates):
        candidates[pt] = fetch_ids(c, pt)
        total += len(candidates[pt])
        print(f"  拉取 {pt!r}: {len(candidates[pt])} 个产品 id")
    all_ids = sorted({i for ids in candidates.values() for i in ids})
    print(f"== 合计去重: {len(all_ids)} 个 active 产品待下架 ==")

    if not go:
        print("（预览模式，加 --go 执行；--go --limit 100 小批验证）")
        return

    todo = [i for i in all_ids if f"gid://shopify/Product/{i}" not in done]
    if limit:
        todo = todo[:limit]
    print(f"== 下架执行: 本轮 {len(todo)} 个（断点跳过后） ==")
    ok = fail = 0
    streak = 0
    for i, pid in enumerate(todo, 1):
        gid = f"gid://shopify/Product/{pid}"
        try:
            r = c.graphql(UPD_MUT, {"product": {"id": gid, "status": "DRAFT"}})
            errs = (r.get("productUpdate") or {}).get("userErrors") or []
            if errs:
                print(f"  ERR {pid}: {errs}")
                fail += 1
                streak += 1
            else:
                ok += 1
                streak = 0
                append_done(gid)
        except Exception as e:  # noqa: BLE001
            print(f"  EXC {pid}: {e}")
            fail += 1
            streak += 1
        if streak >= 10:
            print("!! 连续 10 个失败，熔停（检查 API/权限后重跑续传）")
            break
        if i % 100 == 0:
            print(f"  ... {i}/{len(todo)} ok={ok} fail={fail}")
        time.sleep(0.1)
    print(f"ARCHIVE-DONE 本轮 ok={ok} fail={fail} 断点累计 {len(load_done())}")


if __name__ == "__main__":
    main()
