# -*- coding: utf-8 -*-
"""修复 definition storefront 访问：三连实验找可行 access 组合。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

UPD_MUT = """
mutation DefUpdate($definition: MetafieldDefinitionUpdateInput!) {
  metafieldDefinitionUpdate(definition: $definition) {
    updatedDefinition { id key access { admin storefront } }
    userErrors { field message }
  }
}
"""


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    keys = ["battery_category", "capacity", "voltage", "battery_type",
            "compatible_models", "part_numbers", "watt_hours", "dimensions",
            "net_weight_g"]
    for key in keys:
        res = c.graphql(UPD_MUT, {"definition": {
            "namespace": "custom", "key": key, "ownerType": "PRODUCT",
            "access": {"storefront": "PUBLIC_READ"}}})
        node = (res.get("metafieldDefinitionUpdate") or {})
        errs = node.get("userErrors") or []
        ud = node.get("updatedDefinition") or {}
        acc = (ud.get("access") or {})
        print(f"  {key:22} errs={errs or 'none'} "
              f"admin={acc.get('admin')} storefront={acc.get('storefront')}")
    print("ACCESS-FIX-DONE")


if __name__ == "__main__":
    main()
