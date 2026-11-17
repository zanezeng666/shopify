# -*- coding: utf-8 -*-
"""诊断 819 改价失败：重算 todo → 抽样 vid 查远端存在性。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

svc = PricingService()
dec = svc.build_decisions()
_CS = re.compile(r"CS-([0-9]+)")

todo = []
unchanged = nodec = 0
for vid, sku, cur in svc._variant_cs_ids(1):
    m = _CS.match(sku or "")
    if not m:
        nodec += 1
        continue
    d = dec.get(m.group(1))
    if d is None or d.price is None or d.stopped:
        nodec += 1
        continue
    if cur is not None and abs(float(cur) - d.price) < 0.005:
        unchanged += 1
        continue
    todo.append((vid, sku, cur, d.price))
print(f"todo={len(todo)} unchanged={unchanged} no_decision={nodec}")

client = StoreService().get_client(1)
for vid, sku, cur, new in todo[:4]:
    try:
        r = client.graphql(
            "query($id:ID!){productVariant(id:$id){id sku price product{id status}}}",
            {"id": f"gid://shopify/ProductVariant/{vid}"})
        print(vid, sku, cur, "->", new, "REMOTE:", str(r)[:160])
    except Exception as e:
        print(vid, sku, "ERR", str(e)[:140])
