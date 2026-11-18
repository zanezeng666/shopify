"""对比能出/不能出运费的国家 zone 结构差异。"""
import json
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")

from shopify_admin.services.stores.service import StoreService

client = StoreService().get_client(1)
zones = client.request("GET", "shipping_zones.json").get("shipping_zones", [])

GOOD = {"DE", "GB", "AU", "JP"}
BAD = {"FR", "ES", "NL", "BR", "PL", "NZ"}

for z in zones:
    codes = {c.get("code") for c in z.get("countries", [])}
    tag = None
    if codes & GOOD:
        tag = "OK "
    elif codes & BAD:
        tag = "BAD"
    if tag:
        print(f"\n[{tag}] zone id={z['id']} {z['name']} {sorted(codes)}")
        print("  price_based:", json.dumps(
            z.get("price_based_shipping_rates"), ensure_ascii=False)[:400])
        print("  weight_based:", json.dumps(
            z.get("weight_based_shipping_rates"), ensure_ascii=False)[:500])
        print("  其他键:", [k for k in z.keys()
                          if "rate" not in k and k != "countries"])
