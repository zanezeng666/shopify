# -*- coding: utf-8 -*-
"""补建菜单需要的 3 个小集合（低于 n>=50 门槛但导航需要）。
条件：CDB 美仓该类目产品数 > 0 才建（smart collection, type equals, published）。
幂等：已存在（按规则 condition 匹配）则跳过。
"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

WANTS = ["Game Console Battery", "Keyboard,Mouse Battery",
         "Portable Printer Battery"]  # type 值 = category + " Battery"


def norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def main() -> None:
    from sqlalchemy import text
    from shopify_admin.core.database import get_cs_engine
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    # 美仓类目计数（全仓 status=1 计数一并给出参考）
    cats = [w[: -len(" Battery")] for w in WANTS]
    in_sql = "(" + ",".join(f"'{x}'" for x in cats) + ")"
    with get_cs_engine().connect() as conn:
        rows = conn.execute(text(f"""
            SELECT p.category, COUNT(DISTINCT p.cs_id) n_us,
                   (SELECT COUNT(DISTINCT p2.cs_id) FROM cs_product p2
                    WHERE p2.category = p.category AND p2.status = 1) n_all
            FROM cs_product p
            JOIN (SELECT DISTINCT cs_id FROM cs_inventory
                  WHERE location='US' AND quantity>0) i ON i.cs_id=p.cs_id
            WHERE p.category IN {in_sql} AND p.status=1
            GROUP BY p.category""")).fetchall()
    cnt = {r[0]: (r[1], r[2]) for r in rows}
    for cat in cats:
        n_us, n_all = cnt.get(cat, (0, 0))
        print(f"  {cat!r}: US仓={n_us} 全部在售={n_all}")

    # 现有集合（规则 condition 归一化匹配）
    cols = c.request("GET", "smart_collections.json",
                     params={"limit": 250}).get("smart_collections", [])
    have = set()
    for s in cols:
        rule = (s.get("rules") or [{}])[0]
        if rule.get("column") == "type" and rule.get("condition"):
            have.add(norm(rule["condition"]))
    print(f"现有 type-equals 集合 {len(have)} 个")

    for w in WANTS:
        if norm(w) in have:
            print(f"SKIP {w!r} 已存在")
            continue
        cat = w[: -len(" Battery")]
        n_us, n_all = cnt.get(cat, (0, 0))
        if n_us == 0 and n_all == 0:
            print(f"SKIP {w!r} 无产品（类目不存在），从菜单移除该二级项")
            continue
        try:
            c.request("POST", "smart_collections.json", json_body={
                "smart_collection": {
                    "title": w,
                    "rules": [{"column": "type", "relation": "equals",
                               "condition": w}],
                    "published": True}})
            print(f"[C] 新建 {w!r}（US={n_us} 全部={n_all}）")
        except Exception as e:  # noqa: BLE001
            print(f"[C] ERR {w!r}: {e}")
    print("SMALL-COLS-DONE")


if __name__ == "__main__":
    main()
