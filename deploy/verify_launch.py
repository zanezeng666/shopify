# -*- coding: utf-8 -*-
"""抽验新上架产品在线形态（status/价格/SKU/图/模板）。"""
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

client = ShopifyRest(StoreService().get_client(1)).client
q = """
{
  productByHandle(handle: "%s") {
    status title vendor productType
    variants(first: 3) { nodes { sku price barcode } }
    images(first: 2) { nodes { src } }
    descriptionHtml
  }
}"""
for h in ("battery-for-cecotec-9990-spin-revolution-ultra-power-10090-s",
          "battery-for-delonghi-colombina-evo-xml510-as00000910"):
    r = client.graphql(q % h)
    p = r["productByHandle"] or {}
    if not p:
        print(h, "NOT FOUND")
        continue
    v = p["variants"]["nodes"][0] if p["variants"]["nodes"] else {}
    print(f"== {h[:50]}")
    print(f"   status={p['status']} vendor={p['vendor']} type={p['productType']}")
    print(f"   title={p['title'][:70]}")
    print(f"   sku={v.get('sku')} price={v.get('price')} barcode={v.get('barcode') or '-'}")
    print(f"   images={[i['src'][:60] for i in p['images']['nodes']]}")
    print(f"   desc_len={len(p['descriptionHtml'] or '')}")
