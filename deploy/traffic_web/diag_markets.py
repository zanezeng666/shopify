"""诊断 31 国空 rates: Markets 覆盖假设验证。
自动自省 Market 类型的国家字段，拉取各市场国家清单，与失败国对照。"""
import json
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)


def gql(q, vars=None):
    r = client.graphql(q, vars) if vars else client.graphql(q)
    if not isinstance(r, dict):
        print("GQL 异常返回:", str(r)[:300])
    return r


def leaf_type(t):
    while t.get("ofType"):
        t = t["ofType"]
    return t.get("kind"), t.get("name")


# 1) Market 字段自省 + 自动找国家字段
tm = gql('{ __type(name: "Market") { fields { name type { kind name ofType { kind name ofType { kind name } } } } } }')
fields = tm["__type"]["fields"]
print("Market 字段:", [f["name"] for f in fields])

country_field = None
for f in fields:
    if "countr" in f["name"].lower() or "region" in f["name"].lower():
        kind, tname = leaf_type(f["type"])
        print(f"候选字段 {f['name']}: kind={kind} type={tname}")
        if kind == "OBJECT" and tname:
            sub = gql(f'{{ __type(name: "{tname}") {{ fields {{ name }} }} }}')
            subs = [x["name"] for x in sub["__type"]["fields"]]
            codefield = None
            for c in ("code", "countryCode", "isoCode", "country"):
                if c in subs:
                    codefield = c
                    break
            print(f"  子字段: {subs} -> code字段={codefield}")
            if codefield:
                country_field = (f["name"], codefield)
                break

# 2) Markets 列表 + 国家清单
mk = gql("{ markets(first: 20) { nodes { id handle name enabled } } }")
print("\nMarkets:", json.dumps(mk, ensure_ascii=False))

if country_field:
    fname, cfield = country_field
    q = ("{ markets(first: 20) { nodes { id handle name enabled "
         f"{fname} {{ {cfield} }} }} }}")
    mc = gql(q)
    all_codes = set()
    for m in mc["markets"]["nodes"]:
        codes = sorted({c[cfield] for c in m[fname]})
        all_codes |= set(codes)
        print(f'\nMarket {m["name"]} handle={m.get("handle")} '
              f'enabled={m["enabled"]} countries={len(codes)}:')
        print("  " + ",".join(codes))
    print(f"\n市场覆盖国家总数: {len(all_codes)}")

    bad = ("BR CH CL CO CY DK EE ES FI FR HU IE LT LU LV MD MT MY NL NO NZ "
           "PE PH PL PT RO RS SE SI SK UA").split()
    missing = [c for c in bad if c not in all_codes]
    print(f"31 失败国中不在任何市场: {len(missing)} -> {missing}")
else:
    print("!! 未找到国家字段，需人工看上面字段列表")

# 3) 极简地址重试（排除省码问题）
Q = """
query O($in: DraftOrderAvailableDeliveryOptionsInput!) {
  draftOrderAvailableDeliveryOptions(input: $in) {
    availableShippingRates { title price { amount } }
  }
}
"""
prods = client.request(
    "GET", "products.json?limit=5&fields=id,title,variants")
vin = None
for p in prods.get("products", []):
    for v in p.get("variants", []):
        if v.get("inventory_quantity", 0) > 0:
            vin = v["id"]
            break
    if vin:
        break

print("\n极简地址（仅 country）重试:")
for c in ("FR", "BR", "NL", "PL", "NZ"):
    try:
        r = client.graphql(Q, {"in": {
            "lineItems": [{"variantId":
                           f"gid://shopify/ProductVariant/{vin}",
                           "quantity": 1}],
            "shippingAddress": {"country": c}}})
        rates = r["draftOrderAvailableDeliveryOptions"][
            "availableShippingRates"]
        print(f"  {c}: {[(x['title'], x['price']['amount']) for x in rates]}")
    except Exception as e:
        print(f"  {c}: EXC {str(e)[:100]}")
    time.sleep(0.5)
