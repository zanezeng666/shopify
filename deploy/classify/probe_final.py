# -*- coding: utf-8 -*-
"""终局核实：三类真实 status 分布（REST count）+ 集合真实 productsCount（GraphQL）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

THREE_TYPES = ["Notebook, Laptop Battery", "Mobile, SmartPhone Battery",
               "Camera Battery"]
HANDLES = ["vacuum-battery", "two-way-radio-battery", "power-tools-battery",
           "medical-battery", "tablet-battery", "speaker-battery",
           "barcode-scanner-battery-1", "cordless-phone-battery", "all"]


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)
    print("== 三类真实 status 分布（Shopify REST count）==")
    for t in THREE_TYPES:
        a = c.request("GET", "products/count.json",
                      params={"product_type": t, "status": "active"}).get("count")
        d = c.request("GET", "products/count.json",
                      params={"product_type": t, "status": "draft"}).get("count")
        print(f"  {t:32} active={a}  draft={d}")
    print("== 集合真实 productsCount（GraphQL）==")
    q = '{ c: collectionByHandle(handle: "%s") { title productsCount { count } } }'
    for h in HANDLES:
        try:
            n = (c.graphql(q % h) or {}).get("c")
        except Exception as e:  # noqa: BLE001
            print(f"  {h:30} !! EXC {e}")
            continue
        if n:
            print(f"  {h:30} {str(n.get('title')):30} productsCount={n.get('productsCount')}")
        else:
            print(f"  {h:30} !! 不存在或不可达")


if __name__ == "__main__":
    main()
