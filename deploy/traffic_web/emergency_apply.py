"""紧急恢复: locationGroupsToCreate 单次全量 58 zone（已验证路径）。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

PROFILE_ID = "gid://shopify/DeliveryProfile/25921388644"
LOC_US = "gid://shopify/Location/10117218404"
LOC_HK = "gid://shopify/Location/28661153892"

MUT = """
mutation T($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id version zoneCountryCount }
    userErrors { field message }
  }
}
"""

client = StoreService().get_client(1)
with open("/home/jason/traffic-web/cfg_shipping/plan.json", encoding="utf-8") as f:
    plan = json.load(f)


def zone_input(z):
    methods = []
    for r in z["rates"]:
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
    return {"name": z["name"],
            "countries": [{"code": c, "includeAllProvinces": True}
                          for c in z["countries"]],
            "methodDefinitionsToCreate": methods}


payload = {"locationGroupsToCreate": [{
    "locations": [LOC_US, LOC_HK],
    "zonesToCreate": [zone_input(z) for z in plan["zones"]]}]}
print(f"zones={len(plan['zones'])} payload~{len(json.dumps(payload)) // 1024}KB")

try:
    r = client.graphql(MUT, {"id": PROFILE_ID, "profile": payload})
    p = r.get("deliveryProfileUpdate", {})
    print("result:", json.dumps(p, ensure_ascii=False)[:500])
except Exception as e:
    print("EXC:", str(e)[:400])

zones = client.request("GET", "shipping_zones.json").get("shipping_zones", [])
print("REST zones:", len(zones))
for z in zones[:6]:
    print("  ", z["id"], z["name"], [c.get("code") for c in z.get("countries", [])],
          [(r.get("name", "")[:36], r.get("price")) for r in
           z.get("weight_based_shipping_rates", []) +
           z.get("price_based_shipping_rates", [])][:3])
