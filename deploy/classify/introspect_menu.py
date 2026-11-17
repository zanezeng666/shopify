# -*- coding: utf-8 -*-
"""内省 menuCreate 签名与 MenuItemCreateInput 字段。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

Q = """
{
  menuCreate: __type(name: "Mutation") {
    fields(includeDeprecated: true) {
      name
      args { name type { name kind ofType { name kind } } }
    }
  }
  menuItemInput: __type(name: "MenuItemCreateInput") {
    inputFields { name type { name kind ofType { name kind } } }
  }
  menuUpdate: __type(name: "MenuItemUpdateInput") {
    inputFields { name type { name kind ofType { name kind } } }
  }
}
"""


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    r = c.graphql(Q, {}) or {}
    muts = (r.get("menuCreate") or {}).get("fields") or []
    for f in muts:
        if f["name"].startswith("menu"):
            args = ", ".join(
                f"{a['name']}:{(a['type'].get('ofType') or a['type']).get('name') or a['type'].get('name')}"
                for a in f["args"])
            print(f"{f['name']}({args})")
    print("--- MenuItemCreateInput:")
    for f in (r.get("menuItemInput") or {}).get("inputFields") or []:
        t = f["type"]
        tn = (t.get("ofType") or t).get("name") or t.get("name")
        print(f"  {f['name']}: {tn} ({t['kind']})")
    print("--- MenuItemUpdateInput:")
    for f in (r.get("menuUpdate") or {}).get("inputFields") or []:
        t = f["type"]
        tn = (t.get("ofType") or t).get("name") or t.get("name")
        print(f"  {f['name']}: {tn} ({t['kind']})")


if __name__ == "__main__":
    main()
