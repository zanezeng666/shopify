# -*- coding: utf-8 -*-
"""导出老产品 body_html 完整样本到文件。只读。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text

from shopify_admin.core.database import session_scope

with session_scope() as s:
    r = s.execute(text(
        "SELECT p.title, p.raw FROM products p JOIN product_variants v ON v.product_id=p.id "
        "WHERE v.store_id=1 AND v.sku LIKE 'CS-TMS20SL%' LIMIT 1"
    )).first()

title, raw = r
if isinstance(raw, str):
    import json
    raw = json.loads(raw)
body = (raw or {}).get("body_html") or ""
out = Path(__file__).parent / "_old_body_sample.txt"
out.write_text(f"TITLE: {title}\nLEN: {len(body)}\n{body}", encoding="utf-8")
print(f"written {out} bytes={out.stat().st_size}")
