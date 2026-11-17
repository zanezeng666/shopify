# -*- coding: utf-8 -*-
"""Admin API 实时核对 4 类商品：镜像库 vs 线上状态差异 = MC 无效 URL 来源。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_engine
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

TYPES = [
    "Camera Battery",
    "GPS, Navigator Battery",
    "Mobile, SmartPhone Battery",
    "Ebook, eReader Battery",
    "E-book, E-reader Battery",
]

cl = ShopifyRest(StoreService().get_client(1))

print("=== A) Admin API 实时：4 类 published 产品 ===")
live = {}  # handle -> (id, title, ptype, updated_at)
for pt in TYPES:
    since = 0
    got = 0
    while True:
        r = cl.client.request(
            "GET", "products.json",
            params={"limit": 250, "published_status": "published",
                    "product_type": pt, "since_id": since},
        )
        items = r.get("products", [])
        if not items:
            break
        for p in items:
            live[p["handle"]] = (p["id"], p["title"], pt,
                                 (p.get("updated_at") or "")[:10])
        got += len(items)
        since = items[-1]["id"]
        if len(items) < 250:
            break
        time.sleep(0.5)
    print(f"  {pt:32} published={got}")

print(f"  线上 published 总计 {len(live)}")

print("\n=== B) 镜像库 active vs 线上 ===")
eng = get_engine()
with eng.connect() as c:
    ph = ", ".join(f":t{i}" for i in range(len(TYPES)))
    params = {f"t{i}": t for i, t in enumerate(TYPES)}
    mir = c.execute(text(
        "SELECT handle, status, product_type FROM products "
        f"WHERE product_type IN ({ph}) AND status='active'"), params).all()
print(f"  镜像库 active: {len(mir)}")

mir_h = {r[0] for r in mir}
missing = mir_h - set(live)          # 镜像 active 但线上无 → 已下架/删除 → URL 404
print(f"  镜像 active 但线上已不在 published: {len(missing)}  ◀◀ MC 残留=无效URL")
for h in sorted(missing)[:15]:
    u = f"https://www.estrybattery.com/products/{h}"
    print(f"    {u[:110]}")

# 每类计数
from collections import Counter

miss_type = Counter()
with eng.connect() as c:
    for h in missing:
        t = c.execute(text(
            "SELECT product_type FROM products WHERE handle=:h"),
            {"h": h}).scalar()
        miss_type[t] += 1
print("  按类别:", dict(miss_type))
