# -*- coding: utf-8 -*-
"""只读探测：外部建议清单的数据可行性核查。

1) 镜像库 active 产品的 handle/title 长度分布（验证 PDP 短 URL 建议的事实基础）
2) cs_new 库有无 fitment（机型适配）表/字段（决定查找器/型号SEO页/兼容表可行性）
3) amazon_inventory 的 OEM 机型信息覆盖度（备选数据源）
"""
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine, session_scope


def pct(a, p):
    return a[int(len(a) * p)] if a else 0


def main() -> None:
    # 1) handle/title 长度分布
    with session_scope() as s:
        rows = s.execute(text(
            "SELECT CHAR_LENGTH(handle), CHAR_LENGTH(title) FROM products "
            "WHERE store_id=1 AND status='active'"
        )).all()
    hl = sorted(r[0] for r in rows)
    tl = sorted(r[1] for r in rows)
    print(f"active={len(rows)}")
    if hl:
        print(f"handle: p50={pct(hl,.5)} p90={pct(hl,.9)} p99={pct(hl,.99)} max={hl[-1]} "
              f">115字符={sum(1 for x in hl if x>115)}")
    if tl:
        print(f"title : p50={pct(tl,.5)} p90={pct(tl,.9)} max={tl[-1]} "
              f">70字符={sum(1 for x in tl if x>70)}")

    # 2) cs_new fitment 相关表与列
    with get_cs_engine().connect() as c:
        tabs = [t[0] for t in c.execute(text("SHOW TABLES")).all()]
    fit_tabs = [t for t in tabs if any(
        k in t.lower() for k in ("fit", "compat", "model", "machine", "device", "oem"))]
    print(f"\ncs_new 全部表数={len(tabs)}  fitment相关表: {fit_tabs}")

    with get_cs_engine().connect() as c:
        cols = [r[0] for r in c.execute(text("SHOW COLUMNS FROM cs_product")).all()]
    fit_cols = [x for x in cols if any(
        k in x.lower() for k in ("fit", "compat", "model", "oem", "type", "machine"))]
    print(f"cs_product fitment相关列: {fit_cols}")

    # 3) 逐表深挖：对每个 fitment 相关表看结构与覆盖度
    for t in fit_tabs:
        with get_cs_engine().connect() as c:
            try:
                tc = [r[0] for r in c.execute(text(f"SHOW COLUMNS FROM {t}")).all()]
                cnt = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                print(f"\n表 {t}: {cnt} 行, 列={tc[:14]}")
                # 找 cs_id 关联列
                cs_col = next((x for x in tc if x.lower() in ("cs_id", "csid", "product_id")), None)
                if cs_col and cnt:
                    distinct = c.execute(
                        text(f"SELECT COUNT(DISTINCT {cs_col}) FROM {t}")).scalar()
                    print(f"  distinct {cs_col}={distinct}")
                    sample = c.execute(text(f"SELECT * FROM {t} LIMIT 3")).all()
                    for r in sample:
                        print(f"  样本: {str(r)[:200]}")
            except Exception as e:
                print(f"表 {t} 探测失败: {e}")


if __name__ == "__main__":
    main()
