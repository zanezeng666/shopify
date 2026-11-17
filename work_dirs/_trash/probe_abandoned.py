# -*- coding: utf-8 -*-
"""弃购现状：REST checkouts + GraphQL 探 marketing automation 通路。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

rest = ShopifyRest(StoreService().get_client(1)).client

# 近 30 天弃购（abandoned = 未完成+有商品）
cs = rest.request("GET", "checkouts.json", params={"limit": 50})
rows = cs.get("checkouts", [])
print("recent checkouts:", len(rows))
email_cnt = sum(1 for c in rows if c.get("email"))
total_val = sum(float(c.get("total_price") or 0) for c in rows)
print("with-email:", email_cnt, "total_value:", round(total_val, 2))
for c in rows[:3]:
    print("  ", c.get("created_at", "")[:16], c.get("email"), c.get("total_price"), "items:", len(c.get("line_items", [])))

client = StoreService().get_client(1)
# GraphQL: shop 的 marketing automations 支持探查
try:
    r = client.graphql(
        "{shop{email marketingLists(first:1){nodes{id title}}}}"
    )
    print("ml:", str(r)[:200])
except Exception as e:
    print("ml err:", str(e)[:150])
