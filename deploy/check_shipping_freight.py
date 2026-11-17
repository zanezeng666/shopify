# -*- coding: utf-8 -*-
"""核实两问 (只读, 不改任何配置/价格):
  1. 美国客户当前是否免运费?  -> shipping_zones.json 运费区域规则
  2. 产品价格是否包含运费?    -> PricingService 决策复算 (C/F/P20/P15/定价 构成)
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python check_shipping_freight.py
"""
import statistics
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.pricing.service import PricingService  # noqa: E402

c = ShopifyRest(StoreService().get_client(1)).client


def _rate_desc(r: dict) -> str:
    parts = []
    lo = r.get("min_order_subtotal") or r.get("weight_low")
    hi = r.get("max_order_subtotal") or r.get("weight_high")
    if lo is not None or hi is not None:
        parts.append(f"{lo or 0}~{hi or '∞'}")
    return " ".join(parts)


def check_shipping_zones() -> None:
    print("[1] 店铺运费区域 (REST shipping_zones.json) ...")
    try:
        zs = c.request("GET", "shipping_zones.json").get("shipping_zones", [])
    except Exception as e:  # noqa: BLE001
        print(f"    REST 不可用: {type(e).__name__}: {e}")
        zs = None
    if zs is None:
        print("    尝试 GraphQL deliveryProfiles 备用 ...")
        try:
            r = c.graphql("{ deliveryProfiles(first: 10) { nodes { id name } } }")
            for n in r.get("deliveryProfiles", {}).get("nodes", []):
                print(f"    profile: {n.get('name') or n.get('id')}")
        except Exception as e:  # noqa: BLE001
            print(f"    GraphQL 也不可用: {e}")
        return
    if not zs:
        print("    !! 无任何 shipping zone")
        return
    for z in zs:
        cts = z.get("countries") or []
        codes = ", ".join(cc.get("code", "?") for cc in cts)
        us = any(cc.get("code") == "US" for cc in cts)
        print(f"  zone#{z.get('id')} [{z.get('name')}] 国家({len(cts)}): {codes}")
        rates = z.get("price_based_shipping_rates", []) + z.get("weight_based_shipping_rates", [])
        if not rates:
            print("    !! 该 zone 无运费规则")
        for r in rates:
            tag = "  <-- 美国" if us else ""
            print(f"    - {r.get('name')}: ${r.get('price')} {_rate_desc(r)}{tag}")


def check_price_includes_freight() -> None:
    print("\n[2] 定价决策复算 (口径: 免邮, 运费打进产品价) ...")
    dec = PricingService().build_decisions()
    rows = [d for d in dec.values() if d.price and d.ship_cost and not d.stopped]
    print(f"    有效决策: {len(rows)}")
    print("    样例 (每种定价依据取 2 个):")
    for basis in ("formula20", "amazon_cap", "floor15"):
        picked = [d for d in rows if d.basis == basis][:2]
        for d in picked:
            print(f"      {d.cs_id}: {d.origin}仓 C=${d.cost:.2f} F=${d.ship_cost:.2f} "
                  f"P20=${d.p20:.2f} P15=${d.p15:.2f} -> 定价 ${d.price:.2f} ({basis}) "
                  f"毛利 {d.margin * 100:.1f}% F占价 {d.ship_cost / d.price * 100:.0f}%")
    shares = sorted(d.ship_cost / d.price for d in rows if d.price)
    if shares:
        print(f"    运费占价格比分布 (n={len(shares)}): "
              f"P25 {shares[len(shares) // 4] * 100:.1f}% | "
              f"中位 {statistics.median(shares) * 100:.1f}% | "
              f"P75 {shares[len(shares) * 3 // 4] * 100:.1f}% | "
              f"最高 {shares[-1] * 100:.1f}%")


if __name__ == "__main__":
    check_shipping_zones()
    check_price_includes_freight()
