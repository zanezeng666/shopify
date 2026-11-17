# -*- coding: utf-8 -*-
"""建 9 个产品 metafield definitions（namespace=custom，storefront PUBLIC_READ）。

幂等：先查现有，已存在跳过。用法：
  python create_definitions.py           # 创建缺失的
  python create_definitions.py --purge   # 删除本组 definitions（回滚用）
"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

NS = "custom"

# (key, type, name, description)
DEFS = [
    ("battery_category", "single_line_text_field",
     "Battery Category", "Device category of this replacement battery (e.g. Vacuum Battery)"),
    ("capacity", "single_line_text_field",
     "Capacity", "Rated capacity, e.g. 2600mAh"),
    ("voltage", "single_line_text_field",
     "Voltage", "Nominal voltage, e.g. 3.7V / 7.2V"),
    ("battery_type", "single_line_text_field",
     "Battery Chemistry", "Cell chemistry, e.g. Li-ion / Ni-MH / LiFePO4"),
    ("compatible_models", "list.single_line_text_field",
     "Compatible Models", "Device models this battery fits (from CS fit models)"),
    ("part_numbers", "list.single_line_text_field",
     "Replaces Part Numbers", "OEM part numbers / model numbers replaced by this battery"),
    ("watt_hours", "number_decimal",
     "Watt Hours (Wh)", "Watt-hour rating, useful for shipping compliance"),
    ("dimensions", "single_line_text_field",
     "Dimensions", "Physical dimensions of the battery pack"),
    ("net_weight_g", "number_integer",
     "Net Weight (g)", "Net weight in grams"),
]

CREATE_MUT = """
mutation DefCreate($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id key namespace }
    userErrors { field message }
  }
}
"""

DELETE_MUT = """
mutation DefDelete($id: ID!) {
  metafieldDefinitionDelete(definitionId: $id) {
    deletedDefinitionId
    userErrors { field message }
  }
}
"""


def main() -> None:
    purge = "--purge" in sys.argv
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    existing = c.graphql(
        '{ metafieldDefinitions(first: 100, ownerType: PRODUCT, namespace: "%s")'
        "{ edges { node { id key } } } }" % NS
    )
    have = {e["node"]["key"]: e["node"]["id"]
            for e in ((existing or {}).get("metafieldDefinitions") or {}).get("edges", [])}

    if purge:
        for key, _t, _n, _d in DEFS:
            if key not in have:
                continue
            r = c.graphql(DELETE_MUT, {"id": have[key]})
            errs = (r.get("metafieldDefinitionDelete") or {}).get("userErrors") or []
            print(f"  DEL {key}: {'OK' if not errs else errs}")
        print("PURGE-DONE")
        return

    print("== 现有 custom.* 产品 definitions ==")
    for k in sorted(have):
        print(f"  {k}")
    print(f"  (共 {len(have)} 个，目标 9 个)")

    ok = fail = skip = 0
    for key, typ, name, desc in DEFS:
        if key in have:
            print(f"  SKIP {key} 已存在")
            skip += 1
            continue
        r = c.graphql(CREATE_MUT, {"definition": {
            "name": name, "key": key, "namespace": NS,
            "type": typ, "ownerType": "PRODUCT", "description": desc,
        }})
        node = (r.get("metafieldDefinitionCreate") or {})
        errs = node.get("userErrors") or []
        if errs:
            print(f"  FAIL {key}: {errs}")
            fail += 1
        else:
            d = node.get("createdDefinition") or {}
            print(f"  OK   {key} ({typ}) -> {d.get('id')}")
            ok += 1

    # 复核：重查一遍确认全部就位 + storefront 访问
    again = c.graphql(
        '{ metafieldDefinitions(first: 100, ownerType: PRODUCT, namespace: "%s")'
        "{ edges { node { key access { storefront } } } } }" % NS
    )
    edges = ((again or {}).get("metafieldDefinitions") or {}).get("edges", [])
    final = {e["node"]["key"]: (e["node"].get("access") or {}).get("storefront")
             for e in edges}
    print(f"\n== 结果: 新建 {ok} / 失败 {fail} / 跳过 {skip} ==")
    for key, sf in sorted(final.items()):
        mark = "OK" if sf == "PUBLIC_READ" else "!!"
        print(f"  [{mark}] {key:24} storefront={sf}")
    print("DEFS-DONE")


if __name__ == "__main__":
    main()
