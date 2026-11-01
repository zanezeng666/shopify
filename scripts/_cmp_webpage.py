# -*- coding: utf-8 -*-
"""网页显示维度对比：body_html / images / options（老 active vs 新 draft）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sqlalchemy import text
from shopify_admin.core.database import session_scope
from shopify_admin.services.stores.service import StoreService

svc = StoreService()
client = svc.get_client(1)

with session_scope() as s:
    rows = s.execute(text(
        "SELECT v.shopify_product_id, v.sku FROM product_variants v "
        "WHERE v.sku LIKE 'CS-TVR500VX%' ORDER BY v.id")).all()
by_pid = {}
for pid, sku in rows:
    by_pid.setdefault(pid, []).append(sku)

olds = {pid: sk for pid, sk in by_pid.items() if pid < 10000000000000}
news = {pid: sk for pid, sk in by_pid.items() if pid > 10000000000000}

def dump(tag, pids):
    print(f"===== {tag} ({len(pids)}) =====")
    for i, pid in enumerate(list(pids)[:4]):
        try:
            p = client.request("GET", f"products/{pid}.json", params={"fields": "id,status,handle,options,body_html,images,variants"})["product"]
        except Exception as e:  # noqa: BLE001
            print(f"\n[{pid}] SKIP: {str(e)[:60]}")
            continue
        imgs = p.get("images") or []
        opts = p.get("options") or []
        v0 = (p.get("variants") or [{}])[0]
        body = p.get("body_html") or ""
        print(f"\n[{p.get('status')}] {p.get('handle')} (id={pid})")
        print(f"  images: {len(imgs)} 张" + (f" first={imgs[0].get('width')}x{imgs[0].get('height')} alt={(imgs[0].get('alt') or '')[:30]!r}" if imgs else ""))
        print(f"  options: {[(o.get('name'), o.get('values')) for o in opts]}")
        print(f"  variant.option1={v0.get('option1')!r}")
        print(f"  body_html {len(body)} 字符, 前 300:")
        print("   ", body[:300].replace("\n", "\n    "))
        if i == 0 and tag == "老产品":
            print("  body_html 后 200:")
            print("   ", body[-200:].replace("\n", "\n    "))

dump("老产品", olds)
dump("新产品", news)
