"""introspect draftOrderAvailableDeliveryOptions 签名。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)
q = """
{ __type(name: "DraftOrderAvailableDeliveryOptionsInput") { inputFields {
  name type { name kind ofType { name kind } }
} } }
"""
r = client.graphql(q)
print(json.dumps(r, ensure_ascii=False)[:800])
q2 = """
{ __type(name: "QueryRoot") { fields { name } } }
"""
r2 = client.graphql(q2)
names = [f["name"] for f in r2["__type"]["fields"]]
print("\n包含 available 字段:", [n for n in names if "available" in n.lower()])
