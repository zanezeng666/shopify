# -*- coding: utf-8 -*-
"""库存分布 + to_create 新品交集。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text
from shopify_admin.core.database import get_cs_engine
from shopify_admin.services.products.sync_shopify import CsShopifySyncService

eng = get_cs_engine()
with eng.connect() as c:
    print("== 按仓统计 ==")
    for loc, n, positive, total_q in c.execute(text(
            "SELECT location, COUNT(*), SUM(quantity>0), SUM(quantity) "
            "FROM cs_inventory GROUP BY location ORDER BY 2 DESC")).all():
        print(f"  {loc}: rows={n} positive={positive} total_qty={total_q}")
    print("\n== 多仓重复 cs_id 抽样 ==")
    for r in c.execute(text(
            "SELECT cs_id, COUNT(DISTINCT location) nl FROM cs_inventory "
            "GROUP BY cs_id HAVING nl > 1 LIMIT 5")).all():
        print(" ", r)
    print("\n== quantity 取值分布（负数？0？） ==")
    for r in c.execute(text(
            "SELECT SUM(quantity<0) neg, SUM(quantity=0) zero, SUM(quantity>0) pos "
            "FROM cs_inventory")).all():
        print(" ", r)
    # 更新时间新鲜度
    for r in c.execute(text(
            "SELECT MIN(updated_at), MAX(updated_at) FROM cs_inventory")).all():
        print("  updated_at range:", r)

# 与 to_create 交集
svc = CsShopifySyncService()
d = svc.diff(store_id=1, sample=0)
create_keys = {(i["cs_id"], (i.get("brand") or "").lower()) for i in d["plan"]["to_create"]["items"]}
# sample=0 items 为空 → 重新用 _compute 口径自己算
print("\n== to_create（重算）× cs_inventory 交集 ==")
c2 = svc._compute(1, "report")
creates = c2["to_create"]
with eng.connect() as c:
    inv = {r[0]: int(r[1]) for r in c.execute(text(
        "SELECT cs_id, SUM(quantity) FROM cs_inventory GROUP BY cs_id")).all()}
have = no = 0
for item in creates:
    q = inv.get(item["cs_id"], 0)
    if q > 0:
        have += 1
    else:
        no += 1
print(f"to_create={len(creates)} 有库存={have} 无库存={no}")
# 存量在线产品的库存覆盖情况（对照参考）
on_shelf = {k for k in c2["on_sale"]}
inv_ids = set(inv)
print(f"CS 目录 on_sale={len(on_shelf)} 其中 cs_inventory 有记录={len(on_shelf & inv_ids)}")
