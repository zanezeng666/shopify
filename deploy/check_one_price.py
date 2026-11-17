# -*- coding: utf-8 -*-
"""单产品定价核对：线上价 vs 引擎决策 vs 手工复算（Craftsman 11221）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.pricing.service import PricingService, PricingConfig

HANDLE = "battery-for-craftsman-11221-9-11221-nextec-320-11222"

client = ShopifyRest(StoreService().get_client(1)).client

# 1) 线上价
r = client.graphql("""
query ($h: String!) {
  productByHandle(handle: $h) {
    id
    title
    status
    variants(first: 20) { nodes { sku price inventoryQuantity } }
  }
}""", {"h": HANDLE})
prod = r["productByHandle"]
print("== Shopify 线上 ==")
if not prod:
    print("NOT FOUND:", HANDLE)
    sys.exit()
print(prod["title"], "| status:", prod["status"])
for v in prod["variants"]["nodes"]:
    print(f"  sku={v['sku']} price={v['price']} qty={v['inventoryQuantity']}")

# 2) SKU 反查 cs_id
sku0 = prod["variants"]["nodes"][0]["sku"] or ""
cs_id = sku0.split("_")[0]  # 完整 cs_id 含 CS- 前缀
print(f"\n== cs_id={cs_id} (from {sku0!r}) ==")

# 3) 引擎决策
svc = PricingService()
cfg = PricingConfig.from_settings()
print(f"cfg: margin_std={cfg.margin_std} floor={cfg.margin_floor} "
      f"pay={cfg.pay_rate}+{cfg.pay_fixed} disc={cfg.amzn_discount} "
      f"zone={cfg.shipping_zone} defw={cfg.default_weight_g}")
dec = svc.build_decisions().get(cs_id)
print("\n== 引擎决策 ==")
print(dec.as_dict() if dec else f"no decision for {cs_id}")
if dec and dec.flag == "stopped":
    sys.exit()

# 4) 原始数据
cost, loc = svc.load_costs().get(cs_id, (None, None))
w = svc.load_weights().get(cs_id, 0)
tbl = svc.load_ship_table(cfg.shipping_zone)
ship = svc.ship_fee(w, tbl.get("usps", []), cfg.default_weight_g)
amzn = svc.load_amazon_refs(cfg).get(cs_id)
print(f"\n== 原始数据 == cost={cost}({loc}) weight={w}g ship_usps_zone{cfg.shipping_zone}={ship} amzn_ref={amzn}")

# 5) 手工复算（独立于 build_decisions 再走一遍公式）
if cost and ship is not None:
    m = svc.decide(cost, ship, amzn, cfg)
    print("\n== decide() 复算 ==")
    print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()})
