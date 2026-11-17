# -*- coding: utf-8 -*-
"""全链验证报告（todo 6）。

A. 三类下架统计（镜像 status 分布，active 应≈0）
B. 元字段覆盖率（美仓映射产品样本，nodes 批量读回，按 key 统计填充率）
C. 集合计数抽查（菜单涉及的头部类目集合 products_count>0）
D. 线上断言（/collections/all + 头部集合页 + 样本产品页 HTTP 200）
E. 回滚预案（文本）
用法：python verify_classify.py [--sample 300]
"""
import json
import random
import re
import sys
import time
import urllib.request

sys.path.insert(0, "/home/jason/shopify-admin/src")

SKIP_CATEGORIES = ("Mobile, SmartPhone", "Camera", "Notebook", "Laptop")
THREE_TYPES = ("Notebook, Laptop Battery", "Mobile, SmartPhone Battery",
               "Camera Battery")
BASE = "https://estrybattery.com"
KEYS = ["battery_category", "capacity", "voltage", "battery_type",
        "compatible_models", "part_numbers", "watt_hours", "dimensions",
        "net_weight_g"]
MENU_TITLES = ["Vacuum Battery", "Two-Way Radio Battery", "Power Tools Battery",
               "Medical Battery", "Tablet Battery", "Speaker Battery",
               "Barcode Scanner Battery", "Cordless Phone Battery"]

NODES_Q = """
query N($ids: [ID!]!) {
  nodes(ids: $ids) {
    ... on Product {
      id
      handle
      metafields(namespace: "custom", first: 20) {
        edges { node { key } }
      }
    }
  }
}
"""


def http_ok(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 verify"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return -1


def main() -> None:
    sample_n = 300
    if "--sample" in sys.argv:
        sample_n = int(sys.argv[sys.argv.index("--sample") + 1])
    from sqlalchemy import text
    from shopify_admin.core.database import get_cs_engine, get_engine
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    lines: list[str] = []

    def p(s: str = "") -> None:
        print(s, flush=True)
        lines.append(s)

    # ---- A. 三类下架统计 ----
    in3 = "(" + ",".join(f"'{t}'" for t in THREE_TYPES) + ")"
    with get_engine().connect() as conn:
        rows = conn.execute(text(
            f"SELECT product_type, status, COUNT(*) n FROM products "
            f"WHERE product_type IN {in3} GROUP BY product_type, status"
        )).fetchall()
    p("=" * 60)
    p("A. 三类下架统计（镜像库）")
    active_left = 0
    for t, s, n in sorted(rows):
        p(f"  {t:34} {s:8} {n}")
        if s == "active":
            active_left += n
    p(f"  => 残留 active: {active_left}（应为 0；>0 说明下架未完成）")

    # ---- B. 元字段覆盖率 ----
    skip_sql = "(" + ",".join(f"'{s}'" for s in SKIP_CATEGORIES) + ")"
    with get_cs_engine().connect() as conn:
        us = conn.execute(text(f"""
            SELECT p.cs_id, p.brand FROM cs_product p
            JOIN (SELECT DISTINCT cs_id FROM cs_inventory
                  WHERE location='US' AND quantity>0) i ON i.cs_id=p.cs_id
            WHERE p.cs_id LIKE 'CS-%' AND p.status=1
              AND p.category NOT IN {skip_sql}""")).fetchall()
    with get_engine().connect() as conn:
        vrows = conn.execute(text(
            "SELECT shopify_product_id, sku FROM product_variants "
            "WHERE sku LIKE 'CS-%' AND shopify_product_id IS NOT NULL")).fetchall()
    by_csid = {}
    for v in vrows:
        csid = (v.sku or "").split("_", 1)[0]
        if csid:
            by_csid.setdefault(csid, []).append((v.shopify_product_id, v.sku))
    ids = []
    for r in us:
        csid, brand = str(r[0]), str(r[1]).lower()
        for pid, sku in by_csid.get(csid, ()):
            m = re.match(rf"^{re.escape(csid)}_(.+?)_\d+_\d+$", sku or "")
            if m and m.group(1).lower() == brand:
                ids.append(int(pid))
                break
    ids = list(dict.fromkeys(ids))
    random.Random(42).shuffle(ids)
    sample = ids[:sample_n]
    p("")
    p("=" * 60)
    p(f"B. 元字段覆盖率（美仓映射 {len(ids)} 产品，抽样 {len(sample)}）")
    key_hits = {k: 0 for k in KEYS}
    got = 0
    handle0 = None
    for i in range(0, len(sample), 50):
        batch = [f"gid://shopify/Product/{x}" for x in sample[i:i + 50]]
        res = c.graphql(NODES_Q, {"ids": batch}) or {}
        for node in (res.get("nodes") or []):
            if not node or not node.get("id"):
                continue
            got += 1
            if handle0 is None and node.get("handle"):
                handle0 = node["handle"]
            keys = {e["node"]["key"]
                    for e in (node.get("metafields") or {}).get("edges", [])}
            for k in KEYS:
                if k in keys:
                    key_hits[k] += 1
        time.sleep(0.3)
    if got:
        p(f"  读回成功 {got}/{len(sample)}")
        for k in KEYS:
            pct = key_hits[k] / got * 100
            p(f"  {k:20} {key_hits[k]:5}/{got}  {pct:5.1f}%")
    else:
        p("  !! 样本读回为空，检查映射")

    # ---- C. 集合计数抽查 ----
    cols = c.request("GET", "smart_collections.json",
                     params={"limit": 250}).get("smart_collections", [])
    by_title = {s["title"]: s for s in cols}
    p("")
    p("=" * 60)
    p("C. 集合计数抽查（菜单涉及集合）")
    for t in MENU_TITLES:
        s = by_title.get(t)
        if not s:
            p(f"  {t:30} !! 集合不存在")
        else:
            p(f"  {t:30} products_count={s.get('products_count')} "
              f"handle={s.get('handle')}")

    # ---- D. 线上断言 ----
    p("")
    p("=" * 60)
    p("D. 线上页面断言")
    urls = [f"{BASE}/collections/all"]
    for t in MENU_TITLES[:6]:
        s = by_title.get(t)
        if s and s.get("handle"):
            urls.append(f"{BASE}/collections/{s['handle']}")
    if handle0:
        urls.append(f"{BASE}/products/{handle0}")
    for u in urls:
        p(f"  {http_ok(u):4} {u}")

    # ---- E. 回滚预案 ----
    p("")
    p("=" * 60)
    p("E. 回滚预案")
    p("""  1. 三类恢复：archive_three.py --restore（REST 批量 status=active，幂等）
  2. 元字段清除：按 namespace=custom 批量删除（脚本 --purge 或 GraphQL metafieldsDelete）
  3. 导航回滚：header-group.json 资产值换回 "main-menu" + 后台 Navigation 删 estry-main-menu
  4. 集合：后台删除补建的 3 个 smart collection（产品 type 已改的可用
     fix_types_collections.py 反查 CDB 还原，或保持现状无副作用）""")
    with open("/tmp/classify_verify_report.txt", "w") as f:
        f.write("\n".join(lines))
    p("")
    p(f"VERIFY-DONE（报告已写 /tmp/classify_verify_report.txt）")


if __name__ == "__main__":
    main()
