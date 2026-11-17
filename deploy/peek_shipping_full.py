# -*- coding: utf-8 -*-
"""运费配置前置探查：zones 全貌 + active 产品重量/价格分布（GraphQL 抽样）。"""
import statistics
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService

c = StoreService().get_client(1)

print("== shipping zones 全量 ==")
zs = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
for z in zs:
    ctry = [x.get("code") for x in z.get("countries", [])]
    pr = [(r["name"], r["price"]) for r in z.get("price_based_shipping_rates", [])]
    wr = [(r["name"], r["weight_low"], r["weight_high"], r["price"])
          for r in z.get("weight_based_shipping_rates", [])]
    print(f"  id={z['id']} name={z['name']!r} countries={ctry}")
    if pr or wr:
        print(f"      price_rates={pr}")
        print(f"      weight_rates={wr}")

print("\n== active 产品重量/价格分布（抽样 250 个产品）==")
weights, prices = [], []
prods = c.request("GET", "products.json",
                  params={"limit": 250, "status": "active",
                          "fields": "id,variants"}).get("products", [])
for p in prods:
    for v in p.get("variants", []):
        g = v.get("grams")
        if g is not None:
            weights.append(float(g))
        pv = v.get("price")
        if pv:
            try:
                prices.append(float(pv))
            except (TypeError, ValueError):
                pass

def dist(arr: list, label: str) -> None:
    if not arr:
        print(f"  {label}: 无数据")
        return
    s = sorted(arr)
    n = len(s)
    zero = sum(1 for x in s if x == 0)
    print(f"  {label}: n={n} 零值={zero}({zero*100//n}%) "
          f"min={s[0]:.0f} P25={s[n//4]:.0f} 中位={s[n//2]:.0f} "
          f"P75={s[3*n//4]:.0f} P90={s[int(n*0.9)]:.0f} max={s[-1]:.0f}")

dist(weights, "重量(克)")
dist(prices, "价格(USD)")
