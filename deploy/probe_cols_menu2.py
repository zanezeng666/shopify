# -*- coding: utf-8 -*-
"""收官探测 v2：真实 handle + productsCount + menuByHandle。"""
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    print("== E1. smart collections handle/计数 ==")
    cols = c.request("GET", "smart_collections.json", params={"limit": 250}).get("smart_collections", [])
    targets = {"Vacuum Battery", "Cordless Phone Battery", "Two-Way Radio Battery",
               "Wireless Headset Battery", "Camera Battery", "Power Tools Battery",
               "Medical Battery", "Barcode, Scanner Battery"}
    picks = [s for s in cols if s["title"] in targets]
    alias = " ".join(f"c{i}: collectionByHandle(handle: \"{s['handle']}\") "
                     f"{{ title productsCount {{ count }} }}"
                     for i, s in enumerate(picks[:8]))
    r = c.graphql("{" + alias + "}")
    data = r.get("data", {}) or {}
    for k, v in data.items():
        if v:
            print(f"  {v['title'][:36]!r:40} count={v['productsCount']['count']}")
    errs = r.get("errors")
    if errs:
        print(f"  errors={str(errs)[:200]}")

    print("\n== E2. menuByHandle ==")
    r2 = c.graphql('{ m1: menuByHandle(handle: "main-menu") { title items { title url } } '
                   'm2: menuByHandle(handle: "footer") { title items { title url } } }')
    mdata = r2.get("data", {}) or {}
    for k in ("m1", "m2"):
        m = mdata.get(k)
        if m:
            print(f"  -- {k}: {m['title']!r} --")
            for it in m.get("items", []):
                print(f"    {it['title']!r:26} -> {it.get('url','')[:60]}")

    print("\nFINAL-PROBE-OK")


if __name__ == "__main__":
    main()
