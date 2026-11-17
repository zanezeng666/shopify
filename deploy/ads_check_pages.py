# -*- coding: utf-8 -*-
"""列出 collections 表结构与全部 handle，判断 PMax 落地页是否存在。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_engine

eng = get_engine()
with eng.connect() as c:
    cols = c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name='collections' "
        "ORDER BY ordinal_position")).all()
    print("collections cols:", [r[0] for r in cols])
    names = [r[0] for r in cols]
    hcol = next((x for x in ("handle", "slug") if x in names),
                names[1] if len(names) > 1 else names[0])
    tcol = next((x for x in ("title", "name") if x in names), None)
    rows = c.execute(text(
        f"SELECT `{hcol}`" + (f", `{tcol}`" if tcol else "")
        + " FROM collections ORDER BY 1")).all()
    print(f"total collections: {len(rows)}")
    for r in rows:
        print("  ", r[0], "|", (r[1] if tcol else "")[:50])
