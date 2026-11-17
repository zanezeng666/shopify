# -*- coding: utf-8 -*-
"""收官探测 v3：product_type 计数（REST count）+ 线上导航集合链接（主页 HTML）。"""
import re
import sys
sys.path.insert(0, "/home/jason/shopify-admin/src")


def main() -> None:
    from shopify_admin.services.stores import StoreService
    c = StoreService().get_client(1)

    print("== E1. product_type 计数（REST products/count）==")
    for pt in ("Vacuum Battery", "Cordless Phone Battery", "Two-Way Radio Battery",
               "Power Tools Battery", "Medical Battery", "Barcode, Scanner Battery",
               "Mobile, SmartPhone Battery"):
        n = c.request("GET", "products/count.json",
                      params={"product_type": pt, "status": "active"}).get("count")
        print(f"  {pt!r:32} active={n}")

    print("\n== E2. 线上主页/集合导航链接 ==")
    import httpx
    with httpx.Client(timeout=20, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0 probe"}) as h:
        for url in ("https://estrybattery.com/", "https://estrybattery.com/collections/all"):
            try:
                r = h.get(url)
                links = sorted(set(re.findall(r'href="(/collections/[a-z0-9-]+)"', r.text)))
                print(f"  {url} -> {r.status_code}, /collections 链接 {len(links)} 个")
                for l in links[:25]:
                    print(f"    {l}")
            except Exception as ex:  # noqa: BLE001
                print(f"  {url} ERR {ex}")

    print("\nFINAL3-OK")


if __name__ == "__main__":
    main()
