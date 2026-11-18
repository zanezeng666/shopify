"""诊断空 rates: 远端真实库存 + 完整地址 + market 参数。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

Q = """
query O($in: DraftOrderAvailableDeliveryOptionsInput!) {
  draftOrderAvailableDeliveryOptions(input: $in) {
    availableShippingRates {
      handle title price { amount currencyCode }
    }
  }
}
"""

prods = client.request(
    "GET", "products.json?limit=5&fields=id,title,status,variants")

# 1) 远端真实库存（GraphQL 权威）
for p in prods.get("products", [])[:3]:
    for v in p.get("variants", [])[:2]:
        gid = f"gid://shopify/ProductVariant/{v['id']}"
        try:
            g = client.graphql(
                '{ productVariants(first:1, query:"id:%s") { nodes { id sku '
                'inventoryQuantity (inventory_quantity) } } }'
                % gid.replace("gid://shopify/ProductVariant/", ""))
        except Exception:
            g = client.graphql(
                "query V($q: String!) { productVariants(first:1, query:$q) "
                "{ nodes { id sku inventoryQuantity } } }", {"q": f"id:{gid}"})
        nodes = g.get("productVariants", {}).get("nodes", [])
        print(f"REST qty={v.get('inventory_quantity')} 远端="
              f"{nodes[0]['inventoryQuantity'] if nodes else '未查到'} "
              f"sku={v.get('sku')}")

# 2) 完整地址 + market 参数重试
vin = prods["products"][0]["variants"][0]["id"]
tests = [
    ("裸country", {"lineItems": [{"variantId":
                                  f"gid://shopify/ProductVariant/{vin}",
                                  "quantity": 1}],
                   "shippingAddress": {"country": "US"}}),
    ("完整地址", {"lineItems": [{"variantId":
                                 f"gid://shopify/ProductVariant/{vin}",
                                 "quantity": 1}],
                  "shippingAddress": {"country": "US", "province": "CA",
                                      "city": "Los Angeles",
                                      "zip": "90001",
                                      "address1": "123 Main St"}}),
    ("完整+market", {"lineItems": [{"variantId":
                                    f"gid://shopify/ProductVariant/{vin}",
                                    "quantity": 1}],
                     "shippingAddress": {"country": "US", "province": "CA",
                                         "city": "Los Angeles",
                                         "zip": "90001",
                                         "address1": "123 Main St"},
                     "marketRegionCountryCode": "US"}),
]
for name, payload in tests:
    try:
        r = client.graphql(Q, {"in": payload})
        rates = r["draftOrderAvailableDeliveryOptions"][
            "availableShippingRates"]
        print(f"[{name}] {len(rates)} rates: "
              f"{[(x['title'], x['price']['amount']) for x in rates][:3]}")
    except Exception as e:
        print(f"[{name}] EXC {str(e)[:200]}")
