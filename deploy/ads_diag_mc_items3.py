# -*- coding: utf-8 -*-
"""确认 7194 个 missing 产品：删除 vs draft；Google channel 同步状态。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from sqlalchemy import text

from shopify_admin.core.database import get_engine
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

cl = ShopifyRest(StoreService().get_client(1))

SAMPLES = [
    "battery-for-100-v5-v5100b-100b",
    "battery-for-acer-a755-t205",
    "battery-for-gopro-601-10197-00-aabat-001-aabat-001-as-asst1-",
    "battery-for-jvc-gy-hm200-gy-hm600-gy-hm600e-gy-hm600ec-gy-hm",
]
eng = get_engine()
with eng.connect() as c:
    for h in SAMPLES:
        row = c.execute(text(
            "SELECT id, status, product_type FROM products WHERE handle=:h"),
            {"h": h}).first()
        p = cl.product_by_handle(h)
        if p is None:
            live = "已删除(Admin无)"
        else:
            live = f"status={p.get('status')} published_at={p.get('published_at')}"
        print(f"  {h[:55]:55} 镜像={row[1] if row else '?'} | 线上: {live}")

print("\n=== 店铺 sales channels ===")
try:
    q = "{ shop { channels(first: 20) { edges { node { id name } } } } }"
    r = cl.client.request("POST", "graphql.json", json_={"query": q})
    for e in r.get("data", {}).get("shop", {}).get("channels",
                                                   {}).get("edges", []):
        print(f"  {e['node']['id']:40} {e['node']['name']}")
except Exception as e:  # noqa
    print(f"  GraphQL channels 查询失败: {type(e).__name__}: {e}")
    # 降级：REST publications 不存在，用 shop.json 线索
    print("  (改用 publicationsV2 试探略过)")
