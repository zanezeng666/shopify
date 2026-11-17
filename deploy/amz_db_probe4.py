# -*- coding: utf-8 -*-
"""步骤4：校验争议 cs_id 在 cs_product 的真实品名。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_cs_engine

eng = get_cs_engine()
with eng.connect() as c:
    cols = c.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='cs_new' AND table_name='cs_product' "
        "ORDER BY ordinal_position")).all()
    names = [r[0] for r in cols]
    desc_cols = [x for x in names if any(
        k in x.lower() for k in ("title", "name", "model", "type", "describe",
                                  "machine", "device", "fit", "product"))]
    print("desc-like cols:", desc_cols)
    sel = ", ".join(desc_cols[:6]) if desc_cols else "*"
    rows = c.execute(text(
        f"SELECT cs_id, {sel} FROM cs_new.cs_product "
        "WHERE cs_id IN ('CS-WGF300VX','CS-ABL100VX','CS-TOX500TW',"
        "'CS-P303CL','CS-MVS500VX','CS-EMC150LS') LIMIT 12")).all()
    out = ["cs_id | " + " | ".join(desc_cols[:6])]
    for r in rows:
        out.append(" | ".join(str(x)[:70] if x is not None else "-" for x in r))
    with open("/tmp/amz_probe4.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("saved /tmp/amz_probe4.txt")
