# -*- coding: utf-8 -*-
"""美仓 5236 产品规格元字段全量灌入（后台幂等跑批）。

链路：cs_new.cs_product(US 有库存, 非三类) -> (cs_id, brand)
    -> 镜像 product_variants SKU 映射 -> shopify_product_id -> metafieldsSet
断点：/tmp/classify_enrich_done.txt（shopify_product_id 维度，中断续跑不重不漏）
日志：stdout（nohup 重定向 /tmp/classify_enrich.log）
熔停：连续 10 错或累计错误率 > 2%
用法：python enrich_metafields.py [--limit 50] [--verify-all]
"""
import json
import re
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

SKIP_CATEGORIES = ("Mobile, SmartPhone", "Camera", "Notebook", "Laptop")
DONE_FILE = "/tmp/classify_enrich_done.txt"

SET_MUT = """
mutation MSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key }
    userErrors { field message }
  }
}
"""

GET_META = """
query P($id: ID!) {
  product(id: $id) {
    id
    metafields(namespace: "custom", first: 20) {
      edges { node { key value type } }
    }
  }
}
"""


def one_line(s: str) -> str:
    """single_line_text 禁换行：压平空白并去首尾。"""
    return re.sub(r"\s+", " ", str(s)).strip()


def split_list(raw) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;/]+", str(raw))
    out = []
    for p in parts:
        p = one_line(p)
        if p and p.lower() not in ("n/a", "na", "none", "-"):
            out.append(p)
    return out[:128]  # Shopify list 字段上限 128 元素


def build_values(row: dict) -> list[dict]:
    vals = []
    cat = one_line(row.get("category") or "")
    if cat:
        vals.append(("battery_category", "single_line_text_field", cat))
    for f, k in (("capacity", "capacity"), ("voltage", "voltage"),
                 ("battery_type", "battery_type"), ("dimension", "dimensions")):
        v = row.get(f)
        v = one_line(v) if isinstance(v, str) else v
        if v:
            vals.append((k, "single_line_text_field", str(v)))
    models = split_list(row.get("fit_model"))
    if models:
        vals.append(("compatible_models", "list.single_line_text_field", json.dumps(models)))
    parts = split_list(row.get("part_no"))
    if parts:
        vals.append(("part_numbers", "list.single_line_text_field", json.dumps(parts)))
    wh = row.get("wh_value")
    if wh not in (None, "", 0, "0"):
        try:
            whf = float(wh)
            if whf > 0:
                vals.append(("watt_hours", "number_decimal", str(whf)))
        except (TypeError, ValueError):
            pass
    wg = row.get("net_weight_g")
    if wg not in (None, "", 0, "0"):
        try:
            wgi = int(float(wg))
            if wgi > 0:
                vals.append(("net_weight_g", "number_integer", str(wgi)))
        except (TypeError, ValueError):
            pass
    return vals


def load_done() -> set[int]:
    try:
        with open(DONE_FILE) as f:
            return {int(l.strip()) for l in f if l.strip()}
    except FileNotFoundError:
        return set()


def main() -> None:
    limit = 0
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    verify_all = "--verify-all" in sys.argv

    from sqlalchemy import text
    from shopify_admin.core.database import get_cs_engine, get_engine
    from shopify_admin.services.stores import StoreService

    # 1) CDB 美仓全量（非三类）
    skip_sql = "(" + ",".join(f"'{s}'" for s in SKIP_CATEGORIES) + ")"
    q = f"""
        SELECT p.cs_id, p.brand, p.category, p.capacity, p.voltage, p.battery_type,
               p.fit_model, p.part_no, p.dimension, p.wh_value, p.net_weight_g
        FROM cs_product p
        JOIN (SELECT DISTINCT cs_id FROM cs_inventory
              WHERE location = 'US' AND quantity > 0) i ON i.cs_id = p.cs_id
        WHERE p.cs_id LIKE 'CS-%' AND p.status = 1
          AND p.category NOT IN {skip_sql}
        ORDER BY p.cs_id
    """
    with get_cs_engine().connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(q))]
    print(f"[1] CDB 美仓候选: {len(rows)} 行")

    # 2) 镜像 SKU 全量映射（一次载入内存）
    with get_engine().connect() as conn:
        vrows = conn.execute(text(
            "SELECT shopify_product_id, sku FROM product_variants "
            "WHERE sku LIKE 'CS-%' AND shopify_product_id IS NOT NULL")).fetchall()
    by_csid: dict[str, list[tuple[int, str]]] = {}
    for v in vrows:
        csid = (v.sku or "").split("_", 1)[0]
        if csid:
            by_csid.setdefault(csid, []).append((v.shopify_product_id, v.sku))
    print(f"[2] 镜像 SKU: {len(vrows)} 条, 覆盖 {len(by_csid)} 个 cs_id 前缀")

    # (cs_id, brand) -> product_id
    def locate(r: dict) -> int | None:
        csid = str(r["cs_id"])
        csb = str(r["brand"]).lower()
        for pid, sku in by_csid.get(csid, ()):  # cs_id 含 CS- 前缀，整体为 SKU 首段
            m = re.match(rf"^{re.escape(csid)}_(.+?)_\d+_\d+$", sku or "")
            if m and m.group(1).lower() == csb:
                return int(pid)
        return None

    done = load_done()
    c = StoreService().get_client(1)

    todo = []
    nomap = 0
    for r in rows:
        pid = locate(r)
        if pid is None or pid in done:
            if pid is None:
                nomap += 1
            continue
        todo.append((pid, r))
    if limit:
        todo = todo[:limit]
    print(f"[3] 待写入 {len(todo)}（断点跳过 {len(done)}，镜像无映射 {nomap}）")

    ok = fail = empty = 0
    errs_total = 0
    streak = 0
    t0 = time.time()
    for i, (pid, r) in enumerate(todo, 1):
        vals = build_values(r)
        if not vals:
            empty += 1
            with open(DONE_FILE, "a") as f:
                f.write(f"{pid}\n")
            continue
        gid = f"gid://shopify/Product/{pid}"
        payload = [{"ownerId": gid, "namespace": "custom",
                    "key": k, "type": t, "value": v} for k, t, v in vals]
        try:
            res = c.graphql(SET_MUT, {"metafields": payload}) or {}
            errs = (res.get("metafieldsSet") or {}).get("userErrors") or []
            if errs and all("Owner does not exist" in e.get("message", "")
                            for e in errs):
                # 镜像陈旧（产品已删）：跳过并记断点，不计错误率
                print(f"SKIP_STALE {pid} {r['cs_id']}: product deleted", flush=True)
                with open(DONE_FILE, "a") as f:
                    f.write(f"{pid}\n")
            elif errs:
                print(f"ERR {pid} {r['cs_id']}: {errs}", flush=True)
                fail += 1
                errs_total += 1
                streak += 1
            else:
                ok += 1
                streak = 0
                with open(DONE_FILE, "a") as f:
                    f.write(f"{pid}\n")
                # 抽样读回断言（1/10 或 --verify-all）
                if verify_all or i % 10 == 0:
                    back = c.graphql(GET_META, {"id": gid}) or {}
                    p2 = back.get("product") or {}
                    got = {e["node"]["key"]: e["node"]["value"]
                           for e in (p2.get("metafields") or {}).get("edges", [])}
                    bad = []
                    for k, t, v in vals:
                        gv = got.get(k)
                        if t.startswith("list.") and gv is not None:
                            try:
                                if json.loads(gv) != json.loads(v):
                                    bad.append(k)
                            except ValueError:
                                bad.append(k)
                        elif gv != v:
                            bad.append(k)
                    if bad:
                        print(f"VERIFY {pid} {r['cs_id']} mismatch: {bad}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"EXC {pid} {r['cs_id']}: {e}", flush=True)
            fail += 1
            errs_total += 1
            streak += 1
        if streak >= 10:
            print("!! 连续 10 失败，熔停", flush=True)
            break
        if i % 200 == 0:
            rate = i / max(time.time() - t0, 1)
            pct = errs_total / i * 100
            eta = (len(todo) - i) / max(rate, 0.01) / 60
            print(f"... {i}/{len(todo)} ok={ok} fail={fail} err%={pct:.2f} "
                  f"rate={rate:.1f}/s eta={eta:.0f}min", flush=True)
            if pct > 2 and i >= 100:
                print("!! 错误率超 2%，熔停", flush=True)
                break
        time.sleep(0.12)
    print(f"ENRICH-DONE ok={ok} fail={fail} empty={empty} "
          f"elapsed={(time.time() - t0) / 60:.1f}min 断点累计 {len(load_done())}")


if __name__ == "__main__":
    main()
