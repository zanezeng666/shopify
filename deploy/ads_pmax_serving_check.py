# -*- coding: utf-8 -*-
"""终极验证：PMax 系列实际投放的商品（shopping_performance_view）
→ offerId 的 vid → Shopify product_type 医疗判定。
"""
import os
import re
import time

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")

print("=== 1. PMax 实际投放商品（近30天有展示） ===")
try:
    rs = list(gas.search(customer_id=CID, query=(
        "SELECT shopping_performance_view.offer_id, "
        "metrics.impressions, metrics.clicks, metrics.cost_micros "
        "FROM shopping_performance_view "
        f"WHERE campaign.id = {PMAX} AND metrics.impressions > 0 "
        "AND segments.date BETWEEN '2026-10-13' AND '2026-11-12'")))
    print(f"  有展示的商品数: {len(rs)}")
except Exception as e:  # noqa: BLE001
    print(f"  ✗ {str(e)[:400]}")
    raise SystemExit

total_imp = sum(r.metrics.impressions for r in rs)
total_cost = sum(r.metrics.cost_micros for r in rs) / 1e6
print(f"  总展示 {total_imp:,} 总花费 ¥{total_cost:.2f}")

_V = re.compile(r"shopify_US_\d+_(\d+)$")
vids, by_vid = set(), {}
for r in rs:
    m = _V.match(r.shopping_performance_view.offer_id or "")
    if m:
        v = m.group(1)
        vids.add(v)
        by_vid[v] = (r.metrics.impressions, r.metrics.clicks)
print(f"  可解析 vid: {len(vids)}/{len(rs)}")

print("\n=== 2. vid → Shopify 类型判定 ===")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

sclient = ShopifyRest(StoreService().get_client(1)).client
vmap = {}
vid_list = list(vids)
for i in range(0, len(vid_list), 100):
    ids = [f"gid://shopify/ProductVariant/{v}" for v in vid_list[i:i + 100]]
    q = ("query { nodes(ids: [" +
         ",".join(f'"{g}"' for g in ids) + "]) { ... on ProductVariant "
         "{ product { productType status } } } }")
    r = sclient.graphql(q)
    nodes = r.get("nodes", []) if isinstance(r, dict) else []
    for j, n in enumerate(nodes):
        if n:
            p = n.get("product", {})
            vmap[vid_list[i + j]] = (p.get("productType") or "",
                                     p.get("status") or "")
    time.sleep(0.5)

med_imp = non_imp = unk_imp = 0
non_samples = []
for v, (imp, clk) in by_vid.items():
    pt = vmap.get(v)
    if pt and "medical" in pt[0].lower():
        med_imp += imp
    elif pt:
        non_imp += imp
        if len(non_samples) < 6:
            non_samples.append(f"{pt[0][:24]} imp={imp}")
    else:
        unk_imp += imp
print(f"  展示分布: 医疗品 {med_imp:,} | 非医疗品 {non_imp:,} "
      f"| 未匹配 {unk_imp:,}")
for s in non_samples:
    print(f"    非医疗: {s}")
if non_imp == 0 and med_imp > 0:
    print("  ✓✓ PMax 实际投放 100% 医疗品——非医疗品未获任何展示")
