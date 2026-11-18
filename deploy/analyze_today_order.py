"""拉今天的订单全量归因字段：referring_site/landing_site/note_attributes/client_details/支付方式。只读。"""
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.services.stores.service import StoreService
from shopify_admin.platforms.shopify.rest import ShopifyRest

c = ShopifyRest(StoreService().get_client(1)).client
# 北京 11-18 00:00 = UTC 11-17 16:00；多留余量拉最近 40h
orders = c.request("GET", "orders.json", params={
    "created_at_min": "2026-11-17T08:00:00Z", "status": "any", "limit": 20})["orders"]
print(f"最近40h订单数: {len(orders)}")
for o in orders:
    created = o["created_at"]
    # 只细看北京时间 11-18 的单（UTC 11-17T16:00 之后）
    print("=" * 70)
    print(f"订单 {o['name']} | id={o['id']} | created_at={created}")
    print(f"  金额: {o['total_price']} {o.get('currency')} | 财务: {o['financial_status']} | 履约: {o['fulfillment_status']}")
    print(f"  支付: {o.get('payment_gateway_names')}")
    print(f"  source_name: {o.get('source_name')!r}")
    print(f"  referring_site: {o.get('referring_site')!r}")
    print(f"  landing_site: {o.get('landing_site')!r}")
    print(f"  cancel_reason: {o.get('cancel_reason')!r}")
    na = o.get("note_attributes") or []
    for n in na:
        v = str(n.get("value", ""))[:120]
        print(f"  note_attr[{n.get('name')}]: {v}")
    cd = o.get("client_details") or {}
    print(f"  client: browser={cd.get('browser_ip') and 'ip-set'} lang={cd.get('accept_language')} ua={str(cd.get('user_agent'))[:100]}")
    sh = o.get("shipping_address") or {}
    print(f"  ship: {sh.get('city')}, {sh.get('province_code')}, {sh.get('country_code')}")
    cust = o.get("customer") or {}
    em = cust.get("email") or ""
    print(f"  customer: {cust.get('first_name','')} orders_count={cust.get('orders_count')} email_domain={em.split('@')[-1] if em else '?'}")
    for li in o.get("line_items", []):
        print(f"  item: {li['name'][:70]} | sku={li.get('sku')} qty={li['quantity']} price={li['price']}")
