# -*- coding: utf-8 -*-
"""终态验证：线上 ACTIVE/DRAFT 计数 + 新品抽验（含库存水位）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

rest = ShopifyRest(StoreService().get_client(1))
c = rest.client

# 1) 计数（REST count API）
r = c.request("GET", "products/count.json", params={"status": "active"})
print("线上 ACTIVE 产品数:", r.get("count"))
r = c.request("GET", "products/count.json", params={"status": "draft"})
print("线上 DRAFT 产品数:", r.get("count"))

# 2) 新品抽验（含库存水位——整点任务应已接管）
q = """
{
  productByHandle(handle: "battery-for-delonghi-colombina-evo-xml510-as00000910") {
    status title
    variants(first: 1) { nodes { sku price inventoryQuantity } }
  }
}"""
r = c.graphql(q)
p = r["productByHandle"] or {}
v = (p.get("variants", {}).get("nodes") or [{}])[0]
print("抽验 DeLonghi:", p.get("status"), v.get("sku"), v.get("price"), "qty=", v.get("inventoryQuantity"))
