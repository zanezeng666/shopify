"""①自省 market 相关 mutation + MarketRegionInput 结构；
②MY/PH 换正确省份重测 delivery options。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)


def leaf(t):
    while t.get("ofType"):
        t = t["ofType"]
    return t.get("kind"), t.get("name")


# 1) Mutation 里 market 相关字段
r = client.graphql(
    '{ __type(name: "Mutation") { fields { name } } }')
muts = [f["name"] for f in r["__type"]["fields"] if "arket" in f["name"]]
print("market mutations:", muts)

# 2) marketRegionCreate 参数结构
r2 = client.graphql(
    '{ __type(name: "Mutation") { fields { name args { name type '
    '{ kind name ofType { kind name ofType { kind name } } } } } } }')
for f in r2["__type"]["fields"]:
    if f["name"] in ("marketRegionCreate", "marketRegionUpdate",
                     "marketCreate"):
        print(f"\n{f['name']} args:")
        for a in f["args"]:
            k, tn = leaf(a["type"])
            print(f"  {a['name']}: {k} {tn}")
            if k == "NON_NULL":
                pass
        # input 类型字段
        for a in f["args"]:
            _, tn = leaf(a["type"])
            if tn and "Input" in tn:
                it = client.graphql(
                    '{ __type(name: "%s") { inputFields { name type '
                    '{ kind name ofType { kind name ofType { kind name } } } } } }' % tn)
                print(f"  {tn}:")
                for x in it["__type"]["inputFields"]:
                    print(f"    {x['name']}: {leaf(x['type'])}")

# 3) MY/PH 省份重测
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

CASES = {
    "MY/KL-code": ("MY", "Kuala Lumpur", "50000", "MY-14"),
    "MY/名称": ("MY", "Kuala Lumpur", "50000", "Kuala Lumpur"),
    "MY/无省份": ("MY", "Kuala Lumpur", "50000", None),
    "PH/00": ("PH", "Manila", "1000", "PH-00"),
    "PH/名称": ("PH", "Manila", "1000", "Metropolitan Manila"),
    "PH/无省份": ("PH", "Manila", "1000", None),
}
print("\nMY/PH 省份重测:")
for label, (c, city, zc, prov) in CASES.items():
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
    time.sleep(0.5)
