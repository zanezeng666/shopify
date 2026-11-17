# -*- coding: utf-8 -*-
"""新规则全店重排 dry-run（纯只读，不写任何东西）。

新规则：
  DRAFT: ① product_type ∈ 三类(Mobile/Camera/Notebook) 全部
         ② 其余 ACTIVE 中 非(medical ∨ 近90天出货) → DRAFT
  ACTIVE: ③ 现为 DRAFT 且 非三类 且 (medical ∨ 近90天出货) 且 CS在售 且 非s2停产
  补建:   ④ 无镜像未建品 且 非三类 且 (medical ∨ 近90天出货) 且 CS在售 且 三仓有货
"""
import sys
from collections import Counter

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text  # noqa: E402
from shopify_admin.core.database import (  # noqa: E402
    get_cs_engine, get_engine,
)

with get_cs_engine().connect() as c:
    cols = c.execute(text("SHOW COLUMNS FROM cs_inventory_log")).fetchall()
    print("cs_inventory_log 列:", [r[0] for r in cols])

    # 近90天出货集合（时间列先猜 create_date，脚本内自适应）
    tcol = next((r[0] for r in cols
                 if "date" in r[0].lower() or "time" in r[0].lower()), None)
    print(f"时间列={tcol}")
    sold90 = {r[0] for r in c.execute(text(f"""
        SELECT DISTINCT cs_id FROM cs_inventory_log
        WHERE change_qty < 0 AND {tcol} >= DATE_SUB(NOW(), INTERVAL 90 DAY)
    """))}
    print(f"近90天有出货 csid: {len(sold90)}")

    st_rows = c.execute(text(
        "SELECT cs_id, status, COUNT(*) FROM cs_product GROUP BY cs_id, status"
    )).fetchall()
    # s2: 每 csid 最新 cs_product_record 状态 ∈ 停产集合（对齐 load_stopped）
    s2 = {r[0] for r in c.execute(text("""
        SELECT cs_id FROM cs_product_record p
        WHERE id = (SELECT id FROM cs_product_record q
                    WHERE q.cs_id = p.cs_id ORDER BY id DESC LIMIT 1)
          AND status IN ('Stop Production','Delete','Stop Limit In Stock')
    """))}
    inv3 = {r[0] for r in c.execute(text(
        "SELECT DISTINCT cs_id FROM cs_inventory "
        "WHERE location IN ('US','SZ','HK') AND quantity > 0"))}
cs_stat: dict[str, Counter] = {}
for csid, st, n in st_rows:
    cs_stat.setdefault(csid, Counter())[int(st)] = int(n)
alive = {k for k, v in cs_stat.items() if any(x == 1 for x in v)}

with get_engine().connect() as m:
    rows = m.execute(text(r"""
        SELECT SUBSTRING_INDEX(pv.sku, '_', 1) csid,
               p.status, p.shopify_product_id, p.product_type, p.tags
        FROM product_variants pv
        JOIN products p ON p.id = pv.product_id
        WHERE pv.store_id = 1 AND pv.sku LIKE 'CS-%\_%'
    """)).fetchall()
mirror: dict[str, dict] = {}
for csid, st, spid, ptype, tags in rows:
    d = mirror.setdefault(csid, dict(sts=set(), spids={}, ptype="", tags=""))
    d["sts"].add(st)
    d["spids"][int(spid)] = 1
    d["ptype"] = ptype or ""
    d["tags"] = tags or ""

ptypes = Counter(d["ptype"] for d in mirror.values() if d)
print("\n镜像 product_type 分布(ACTIVE/DRAFT 拆分):")
for t, n in ptypes.most_common(40):
    act = sum(1 for d in mirror.values()
              if d["ptype"] == t and "active" in d["sts"])
    print(f"  {str(t)[:36]:38} 总{n:>5} 在架{act:>5}")

THREE = {"mobile smartphone battery", "camera battery",
         "notebook,laptop battery"}

def is_med(d):
    return "ad-medical" in (d["tags"] or "") or "medical" in d["ptype"].lower()

def in_three(d):
    return d["ptype"].strip().lower() in THREE

to_draft, to_active, skipped_three_draft = [], [], 0
for csid, d in mirror.items():
    three = in_three(d)
    act = "active" in d["sts"]
    keep = is_med(d) or csid in sold90
    if act:
        if three:
            to_draft.append((csid, "三类"))
        elif not keep:
            to_draft.append((csid, "无出货非医疗"))
    elif three:
        skipped_three_draft += 1  # 已是 draft 的三类,维持
    else:
        if keep and csid in alive and csid not in s2:
            to_active.append(csid)

print(f"\n== 新规则重排结果 ==")
print(f"① 转 DRAFT(三类在架): {sum(1 for _, w in to_draft if w=='三类')}")
print(f"② 转 DRAFT(非医疗且近90天无出货): "
      f"{sum(1 for _, w in to_draft if w=='无出货非医疗')}")
print(f"③ 恢复 ACTIVE(误伤+符合新规): {len(to_active)}")
print(f"   三类已是DRAFT维持: {skipped_three_draft}")
act_med = sum(1 for x in to_active if is_med(mirror[x]))
print(f"   其中医疗 {act_med} / 近90天出货 {len(to_active)-act_med}")

# ④ 补建清单
with get_cs_engine().connect() as c:
    cat = c.execute(text(
        "SELECT DISTINCT cs_id, category FROM cs_product WHERE status = 1"
    )).fetchall()
cat_by_csid = {}
for csid, catg in cat:
    cat_by_csid.setdefault(csid, set()).add(str(catg or ""))
THREE_CAT = {"Mobile, SmartPhone Battery", "Camera Battery",
             "Notebook, Laptop Battery"}
to_create = [csid for csid in sold90 | {k for k in mirror if False}
             if csid not in mirror
             and csid in alive and csid not in s2
             and not (cat_by_csid.get(csid, set()) & THREE_CAT)
             and (csid in inv3)]
print(f"④ 补建新品(未建品∩新规∩三仓有货): {len(to_create)}")
