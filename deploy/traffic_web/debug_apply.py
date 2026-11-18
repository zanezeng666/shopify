"""查当前 profile 的 location groups 归属。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)
r = client.graphql("""
{ deliveryProfile(id: "gid://shopify/DeliveryProfile/25921388644") {
    id name version zoneCountryCount
    profileLocationGroups {
      locationGroup {
        id
        locations(first: 20) { nodes { id name } }
      }
    }
} }""")
print(json.dumps(r, ensure_ascii=False, indent=1))

zones = client.request("GET", "shipping_zones.json").get("shipping_zones", [])
print("REST zones:", [(z["id"], z["name"],
                       [c.get("code") for c in z.get("countries", [])]) for z in zones])
