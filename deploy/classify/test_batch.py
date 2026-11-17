# -*- coding: utf-8 -*-
"""测试批：美仓 Vacuum 20 个产品定位 -> metafieldsSet 写 9 字段 -> 读回断言 -> type 未变断言。

数据链：cs_new.cs_product(+cs_inventory US) -> (cs_id, brand)
      -> shopify_new.product_variants.sku 'CS-{csid}_{Brand}_...' -> shopify product_id
"""
import json
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

SKIP_CATEGORIES = ("Mobile, SmartPhone", "Camera", "Notebook", "Laptop")

SET_MUT = """
mutation MSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key namespace }
    userErrors { field message }
  }
}
"""

GET_META = """
query P($id: ID!) {
  product(id: $id) {
    id
    title
    productType
    status
    metafields(namespace: "custom", first: 20) {
      edges { node { key value type } }
    }
  }
}
"""


def split_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    parts = re.split(r"[,;/]+", str(raw))
    out = []
    for p in parts:
        p = p.strip()
        if p and p.lower() not in ("n/a", "na", "none", "-"):
            out.append(p)
    return out


def build_values(row: dict) -> list[dict]:
    """cs_product 行 -> metafieldsSet 输入（空字段跳过）。"""
    vals = []
    cat = (row.get("category") or "").strip()
    if cat:
        vals.append(("battery_category", "single_line_text_field", cat))
    for f, k in (("capacity", "capacity"), ("voltage", "voltage"),
                 ("battery_type", "battery_type"), ("dimension", "dimensions")):
        v = (row.get(f) or "").strip() if isinstance(row.get(f), str) else row.get(f)
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


def main() -> None:
    from sqlalchemy import text
    from shopify_admin.core.database import get_cs_engine, get_engine
    from shopify_admin.services.stores import StoreService

    # 1) CDB：美仓 Vacuum 头 20 条
    cs = get_cs_engine()
    skip_sql = "(" + ",".join(f"'{s}'" for s in SKIP_CATEGORIES) + ")"
    q = f"""
        SELECT p.cs_id, p.brand, p.category, p.capacity, p.voltage, p.battery_type,
               p.fit_model, p.part_no, p.dimension, p.wh_value, p.net_weight_g
        FROM cs_product p
        JOIN (SELECT DISTINCT cs_id FROM cs_inventory
              WHERE location = 'US' AND quantity > 0) i ON i.cs_id = p.cs_id
        WHERE p.cs_id LIKE 'CS-%' AND p.status = 1
          AND p.category NOT IN {skip_sql}
          AND p.category LIKE 'Vacuum%'
        ORDER BY p.cs_id
        LIMIT 20
    """
    with cs.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(q))]
    print(f"== 1) CDB 美仓 Vacuum 候选: {len(rows)} 条 ==")
    if rows:
        r0 = rows[0]
        print(f"  样例: cs_id={r0['cs_id']} category={r0['category']!r} "
              f"cap={r0['capacity']!r} volt={r0['voltage']!r} chem={r0['battery_type']!r}")
        print(f"  fit_model 样例: {str(r0['fit_model'])[:100]!r}")
        print(f"  part_no 样例: {str(r0['part_no'])[:60]!r}  wh={r0['wh_value']!r}  "
              f"weight={r0['net_weight_g']!r}  dim={str(r0['dimension'])[:40]!r}")

    # 2) 镜像定位：sku = {cs_id}_{Brand}_{N}_{M}（cs_id 含 CS- 前缀）
    eng = get_engine()
    ids = [r["cs_id"] for r in rows]
    like_any = " OR ".join(f"sku LIKE '{i}\\_%'" for i in ids)
    with eng.connect() as conn:
        vrows = conn.execute(text(
            f"SELECT shopify_product_id, sku FROM product_variants WHERE ({like_any})"
        )).fetchall()
    # key=(cs_id, brand.lower()) -> shopify_product_id；同 cs_id 不同品牌是不同产品
    sku_map: dict[tuple[str, str], int] = {}
    for v in vrows:
        for csid in ids:
            m = re.match(rf"^{re.escape(csid)}_(.+?)_\d+_\d+$", v.sku or "")
            if not m:
                continue
            sku_map.setdefault((csid, m.group(1).lower()), v.shopify_product_id)
    print(f"== 2) 镜像定位: {len(sku_map)}/{len(ids)} 个 cs_id 找到 product_id ==")

    # 3) 写 metafields + 读回断言
    c = StoreService().get_client(1)
    ok = fail = skipped = 0
    field_hits: dict[str, int] = {}
    for r in rows:
        pid = sku_map.get((r["cs_id"], str(r["brand"]).lower()))
        if not pid:
            skipped += 1
            print(f"  SKIP-NOMAP {r['cs_id']} brand={r['brand']!r}")
            continue
        before = c.graphql(GET_META, {"id": f"gid://shopify/Product/{pid}"})
        prod = (before or {}).get("product") or {}
        vals = build_values(r)
        if not vals:
            print(f"  EMPTY gid {pid} {r['cs_id']}")
            skipped += 1
            continue
        gid = f"gid://shopify/Product/{pid}"
        payload = [{"ownerId": gid, "namespace": "custom",
                    "key": k, "type": t, "value": v} for k, t, v in vals]
        res = c.graphql(SET_MUT, {"metafields": payload})
        errs = (res.get("metafieldsSet") or {}).get("userErrors") or []
        if errs:
            print(f"  ERR gid {pid} {r['cs_id']}: {errs}")
            fail += 1
            continue
        # 读回断言
        after = c.graphql(GET_META, {"id": gid})
        p2 = (after or {}).get("product") or {}
        got = {e["node"]["key"]: e["node"]["value"]
               for e in (p2.get("metafields") or {}).get("edges", [])}
        mism = []
        for k, t, v in vals:
            gv = got.get(k)
            if t.startswith("list.") and gv is not None:
                # list 值比较解析后的数组（Shopify 归一化 JSON 无空格）
                try:
                    if json.loads(gv) != json.loads(v):
                        mism.append((k, v[:40], str(gv)[:40]))
                except ValueError:
                    mism.append((k, v[:40], str(gv)[:40]))
            elif gv != v:
                mism.append((k, v[:40], str(gv)[:40]))
        type_ok = p2.get("productType") == prod.get("productType")
        status_ok = p2.get("status") == "ACTIVE"
        if mism or not type_ok or not status_ok:
            print(f"  VERIFY-FAIL gid {pid} {r['cs_id']}: mism={mism} "
                  f"type_stable={type_ok} active={status_ok}")
            fail += 1
        else:
            ok += 1
            for k, _t, _v in vals:
                field_hits[k] = field_hits.get(k, 0) + 1
            print(f"  OK gid {pid} {r['cs_id']} {str(p2.get('title'))[:44]!r} "
                  f"fields={len(vals)}")

    print(f"\n== 3) 结果: OK {ok} / FAIL {fail} / SKIP {skipped} ==")
    print("  字段命中: " + ", ".join(f"{k}={v}" for k, v in sorted(field_hits.items())))
    print("TEST-BATCH-DONE")


if __name__ == "__main__":
    main()
