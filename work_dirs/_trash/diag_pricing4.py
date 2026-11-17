# -*- coding: utf-8 -*-
"""抽样 819 中的 vid/pid 对账远端：谁不存在、pid 是否错位。"""
import re
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.pricing import PricingService  # noqa: E402
from shopify_admin.services.stores.service import StoreService  # noqa: E402

svc = PricingService()
dec = svc.build_decisions()
_CS = re.compile(r"^(CS-[A-Za-z0-9]+)")

todo = []
for vid, sku, cur in svc._variant_cs_ids(1):
    m = _CS.match(sku or "")
    if not m:
        continue
    d = dec.get(m.group(1))
    if d is None or d.price is None or d.stopped:
        continue
    if cur is not None and abs(float(cur) - d.price) < 0.005:
        continue
    todo.append((vid, sku, cur, d.price))
print("todo:", len(todo))

# pid 来源（与 _push 相同）
from shopify_admin.models.product import ProductVariant  # noqa: E402
from shopify_admin.core.database import session_scope  # noqa: E402
from sqlalchemy import select  # noqa: E402
with session_scope() as s:
    rows = s.execute(select(ProductVariant.shopify_variant_id, ProductVariant.shopify_product_id)
                     .where(ProductVariant.store_id == 1)).all()
vid2pid = {r[0]: r[1] for r in rows}

client = StoreService().get_client(1)
for vid, sku, cur, new in todo[:5]:
    pid = vid2pid.get(vid)
    try:
        r = client.graphql(
            "query($p:ID!,$v:ID!){product(id:$p){id status} productVariant(id:$v){id price}}",
            {"p": f"gid://shopify/Product/{pid}", "v": f"gid://shopify/ProductVariant/{vid}"})
        print(vid, sku[:26], cur, "->", new, "| pid:", pid, "| R:", str(r)[:170])
    except Exception as e:
        print(vid, sku[:26], "ERR", str(e)[:140])
