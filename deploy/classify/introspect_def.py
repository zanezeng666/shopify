# -*- coding: utf-8 -*-
"""introspect MetafieldAdminAccessInput / MetafieldStorefrontAccessInput 真实枚举值。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

Q = """
{
  a: __type(name: "MetafieldAdminAccessInput") { enumValues { name } }
  s: __type(name: "MetafieldStorefrontAccessInput") { enumValues { name } }
}
"""


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    r = c.graphql(Q) or {}
    print("AdminInput:", [e["name"] for e in (r.get("a") or {}).get("enumValues") or []])
    print("StorefrontInput:", [e["name"] for e in (r.get("s") or {}).get("enumValues") or []])


if __name__ == "__main__":
    main()
