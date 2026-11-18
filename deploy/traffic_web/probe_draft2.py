"""draftOrderAvailableDeliveryOptions 结账模拟: 先探 US 结构。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

# 1) 找一个在售有货 variant
prods = client.request("GET", "products.json?limit=10&fields=id,handle,title,variants")
variant = None
for p in prods.get("products", []):
    for v in p.get("variants", []):
        if v.get("inventory_quantity", 0) > 0:
            variant = (p["title"], v["id"])
            break
    if variant:
        break
print("测试产品:", variant)

Q = """
query O($in: DraftOrderAvailableDeliveryOptionsInput!) {
  draftOrderAvailableDeliveryOptions(input: $in) {
    availableShippingRates {
      handle
      title
      price { amount currencyCode }
    }
  }
}
"""
vin = variant[1]
r = client.graphql(Q, {"in": {
    "lineItems": [{"variantId": f"gid://shopify/ProductVariant/{vin}",
                   "quantity": 1}],
    "shippingAddress": {"country": "US"},
}})
print(json.dumps(r, ensure_ascii=False, indent=1)[:1500])
