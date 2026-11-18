"""PE 残留问题诊断: zone 费率配置 + 省份码变体重试。"""
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)

# 1) REST zone 里 PE 的费率
zs = client.request("GET", "shipping_zones.json")
for z in zs.get("shipping_zones", []):
    cs = {c["code"] for c in z.get("countries", [])}
    if "PE" in cs:
        print(f'zone "{z["name"]}" 国家: {sorted(cs)}')
        for r in z.get("price_based_shipping_rates", []):
            print(f"  price-based: {r['name']} min={r.get('min_order_subtotal')} "
                  f"max={r.get('max_order_subtotal')} price={r['price']}")
        for r in z.get("weight_based_shipping_rates", []):
            print(f"  weight-based: {r['name']} "
                  f"{r.get('weight_low')}/{r.get('weight_high')}g "
                  f"price={r['price']}")

# 2) 省份变体
Q = """
query O($in: DraftOrderAvailableDeliveryOptionsInput!) {
  draftOrderAvailableDeliveryOptions(input: $in) {
    availableShippingRates { title price { amount } }
  }
}
"""
prods = client.request(
    "GET", "products.json?limit=5&fields=id,variants")
vin = None
for p in prods.get("products", []):
    for v in p.get("variants", []):
        if v.get("inventory_quantity", 0) > 0:
            vin = v["id"]
            break
    if vin:
        break

CASES = [
    ("Lima省份名", "PE", "Lima", "15001", "Lima"),
    ("LIM码", "PE", "Lima", "15001", "PE-LIM"),
    ("LMA码", "PE", "Lima", "15001", "PE-LMA"),
    ("无省份", "PE", "Lima", "15001", None),
    ("大区Miraflores", "PE", "Miraflores", "15074", "PE-LIM"),
]
print("\nPE 省份重测:")
for label, c, city, zc, prov in CASES:
    sa = {"country": c, "city": city, "zip": zc, "address1": "123 Main St"}
    if prov:
        sa["province"] = prov
    try:
        rr = client.graphql(Q, {"in": {
            "lineItems": [{"variantId":
                           f"gid://shopify/ProductVariant/{vin}",
                           "quantity": 1}],
            "shippingAddress": sa}})
        rates = rr["draftOrderAvailableDeliveryOptions"][
            "availableShippingRates"]
        print(f"  {label}: {[(x['title'], x['price']['amount']) for x in rates]}")
    except Exception as e:
        print(f"  {label}: EXC {str(e)[:120]}")
    time.sleep(0.6)
