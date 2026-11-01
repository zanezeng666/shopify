# -*- coding: utf-8 -*-
"""老品 body_html 完整结构 + 新品完整 body_html + CS 图片字段探查。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import session_scope
from shopify_admin.services.stores.service import StoreService
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

svc = StoreService()
client = svc.get_client(1)

# 老品完整 body_html（Amarey，最能代表模板）
p_old = client.request("GET", "products/7122951831719.json",
                       params={"fields": "body_html"})["product"]
print("===== 老品 body_html 完整 =====")
print(p_old.get("body_html"))

# 新品完整 body_html
p_new = client.request("GET", "products/15476051214580.json",
                       params={"fields": "body_html"})["product"]
print("\n===== 新品 body_html 完整 =====")
print(p_new.get("body_html"))

# 另两个老品 body_html 的差异部分（确认模板一致性，抽出表头行）
for pid in (7123954434215, 7124086456487):
    b = client.request("GET", f"products/{pid}.json",
                       params={"fields": "body_html"})["product"].get("body_html") or ""
    print(f"\n===== 老品 {pid} body_html 前 600 =====")
    print(b[:600])

# CS 数据源图片字段
print("\n===== CS 图片字段探查（CS-TVR500VX 前 5 行）=====")
sync = CsShopifySyncService()
with sync._cs_session() as s:  # noqa: SLF001
    rows = s.execute(text(
        "SELECT * FROM cs_product WHERE cs_id='CS-TVR500VX' LIMIT 5")).all()
    cols = rows[0]._fields if rows else ()
    print("列:", cols)
    for r in rows[:3]:
        d = dict(r._mapping)
        for k, v in d.items():
            if "img" in k.lower() or "pic" in k.lower() or "photo" in k.lower() or "url" in k.lower():
                print(f"  {k} = {str(v)[:100]}")
        print("  ---")
