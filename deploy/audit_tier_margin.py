# -*- coding: utf-8 -*-
"""数量阶梯折扣毛利红线审计 (只读, 不改任何价格).

  线上 ACTIVE 变体现价 × (1 - 档位折扣) vs PricingService P15 底价:
  击穿 = 折后价 < P15 (15% 净利率红线).
  四档统计 + 8%/10% 档击穿 SKU 明细 CSV (现价-底价空间从小到大).
用法:
  sudo -u jason env HOME=/home/jason .venv/bin/python audit_tier_margin.py
"""
import csv
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402
from shopify_admin.services.pricing.service import PricingService  # noqa: E402

TIERS = [(10, 5.0), (20, 6.0), (50, 8.0), (100, 10.0)]
TOL = 0.005  # 分级容差

c = ShopifyRest(StoreService().get_client(1)).client


def iter_active_variant_prices():
    cur = None
    while True:
        r = c.graphql(
            """query ($n: Int!, $cur: String) {
              products(first: $n, after: $cur, query: "status:active") {
                pageInfo { hasNextPage endCursor }
                nodes { variants(first: 30) { nodes { sku price } } }
              }
            }""",
            {"n": 100, "cur": cur},
        )
        p = r["products"]
        for prod in p["nodes"]:
            for v in prod["variants"]["nodes"]:
                if v.get("sku") and v.get("price"):
                    yield v["sku"], float(v["price"])
        if not p["pageInfo"]["hasNextPage"]:
            return
        cur = p["pageInfo"]["endCursor"]


def main() -> None:
    print("[1] 引擎决策加载 ...")
    dec = PricingService().build_decisions()
    by_cs = {k: v for k, v in dec.items() if v.p15 and v.price and v.flag != "stopped"}
    print(f"    可比价决策: {len(by_cs)}")

    print("[2] 线上 ACTIVE 变体价格分页拉取 ...")
    online: dict[str, float] = {}
    n_v = 0
    for sku, price in iter_active_variant_prices():
        n_v += 1
        cs = sku.split("_")[0]
        if cs not in online or price < online[cs]:  # 同 cs_id 取最低价(最保守)
            online[cs] = price
    print(f"    变体 {n_v} -> cs_id {len(online)}")

    rows = [(cs, p, by_cs[cs]) for cs, p in online.items() if cs in by_cs]
    print(f"    线上可对账 cs_id: {len(rows)}")

    print("[3] 四档击穿统计 (折后价 < P15):")
    breach: dict[float, list] = {pct: [] for _, pct in TIERS}
    for cs, cur_price, d in rows:
        for _, pct in TIERS:
            after = cur_price * (1 - pct / 100.0)
            if after < d.p15 - TOL:
                breach[pct].append((cs, cur_price, round(after, 2), round(d.p15, 2)))
    total = len(rows)
    for qty, pct in TIERS:
        b = breach[pct]
        pct_str = f"{(len(b) / total * 100 if total else 0):.1f}%"
        print(f"    {qty}+件 -{pct:g}%: 击穿 {len(b)}/{total} ({pct_str})")

    out = "/home/jason/shopify-admin/deploy/tier_margin_breach.csv"
    n = 0
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cs_id", "tier", "online_price", "price_after_discount", "p15_floor", "shortfall"])
        for qty, pct in sorted(TIERS, reverse=True):
            if pct not in (8.0, 10.0):
                continue
            for cs, cp, after, p15 in sorted(breach[pct], key=lambda x: x[1] - x[3]):
                w.writerow([cs, f"{qty}+ -{pct:g}%", f"{cp:.2f}", after, p15, f"{after - p15:.2f}"])
                n += 1
    print(f"[4] 8%/10% 档击穿明细 -> {out} ({n} 行, 现价-底价空间最小在前)")
    for cs, cp, after, p15 in breach[10.0][:10]:
        print(f"    10%档样例: {cs} 现价{cp:.2f} 折后{after:.2f} < P15 {p15:.2f}")
    print("AUDIT-TIER-MARGIN-DONE")


if __name__ == "__main__":
    main()
