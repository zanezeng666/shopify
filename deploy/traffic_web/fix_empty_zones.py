"""诊断: 找 rates 空的 zone 并补 method。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

PROFILE_ID = "gid://shopify/DeliveryProfile/25921388644"
MUT = """
mutation T($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id version zoneCountryCount }
    userErrors { field message }
  }
}
"""
client = StoreService().get_client(1)
zones = client.request("GET", "shipping_zones.json").get("shipping_zones", [])
empty = []
for z in zones:
    rates = z.get("price_based_shipping_rates", []) + z.get("weight_based_shipping_rates", [])
    if not rates:
        empty.append((z["id"], z["name"], [c.get("code") for c in z.get("countries", [])]))
print("rates 空的 zone:", empty)

with open("/home/jason/traffic-web/cfg_shipping/plan.json", encoding="utf-8") as f:
    plan = json.load(f)
plan_by_code = {z["countries"][0]: z for z in plan["zones"]}

FIX = False
if len(sys.argv) > 1 and sys.argv[1] == "--fix" and empty:
    FIX = True

if FIX:
    for zid, zname, codes in empty:
        pz = plan_by_code.get(codes[0])
        if not pz:
            print("plan 缺:", codes)
            continue
        methods = []
        for r in pz["rates"]:
            m = {"name": r["name"], "active": True,
                 "rateDefinition": {"price": {"amount": f"{r['price']:.2f}",
                                              "currencyCode": "USD"}}}
            conds = []
            if r.get("low_kg") is not None:
                conds.append({"criteria": {"value": r["low_kg"], "unit": "KILOGRAMS"},
                              "operator": "GREATER_THAN_OR_EQUAL_TO"})
            if r.get("high_kg") is not None:
                conds.append({"criteria": {"value": r["high_kg"], "unit": "KILOGRAMS"},
                              "operator": "LESS_THAN_OR_EQUAL_TO"})
            if conds:
                m["weightConditionsToCreate"] = conds
            methods.append(m)
        payload = {"profileLocationGroups": [{
            "id": "gid://shopify/DeliveryLocationGroup/119649698036",
            "zonesToUpdate": [{
                "id": f"gid://shopify/DeliveryZone/{zid}",
                "methodDefinitionsToCreate": methods}]}]}
        try:
            r = client.graphql(MUT, {"id": PROFILE_ID, "profile": payload})
            p = r.get("deliveryProfileUpdate", {})
            print(f"fix {codes}: errs={json.dumps(p.get('userErrors'))[:200]} "
                  f"ver={(p.get('profile') or {}).get('version')}")
        except Exception as e:
            print(f"fix {codes}: EXC {str(e)[:200]}")

    zones = client.request("GET", "shipping_zones.json").get("shipping_zones", [])
    for z in zones:
        rates = z.get("price_based_shipping_rates", []) + \
            z.get("weight_based_shipping_rates", [])
        if not rates:
            print("仍空:", z["id"], z["name"])
    print("重查完成")
