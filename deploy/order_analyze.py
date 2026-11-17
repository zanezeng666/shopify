# -*- coding: utf-8 -*-
"""首单归因分析：订单明细 / GA4 purchase 会话归因 / Ads 近3日转化 / 今日干净口径。"""
import os
import sys

import httpx
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

sys.path.insert(0, "/home/jason/shopify-admin")
from shopify_admin.services.stores.service import StoreService  # noqa: E402
from shopify_admin.platforms.shopify.rest import ShopifyRest  # noqa: E402

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
GA4 = "313397200"

c = ShopifyRest(StoreService().get_client(1)).client

# ---------- 1. Shopify 订单明细 ----------
orders = c.request("GET", "orders.json", params={
    "status": "any", "created_at_min": "2026-11-01T00:00:00Z",
    "limit": 50}).get("orders", [])
print(f"=== 1. 订单 {len(orders)} 个（2026-11-01 以来）===")
for o in orders:
    ship = (o.get("total_shipping_price_set", {})
            .get("shop_money", {}).get("amount", "?"))
    print(f"\n-- {o['name']} id={o['id']} {o['created_at']} "
          f"fin={o['financial_status']} ful={o.get('fulfillment_status')}")
    print(f"   total=${o['total_price']} sub=${o['subtotal_price']} "
          f"ship=${ship} {o['currency']}")
    if o.get("discount_codes"):
        print(f"   折扣: {o['discount_codes']}")
    print(f"   支付: {o.get('payment_gateway_names')} "
          f"locale={o.get('customer_locale')}")
    sa = o.get("shipping_address") or {}
    print(f"   地址: {sa.get('country_code')} {sa.get('province', '')} "
          f"{sa.get('city', '')}")
    cu = o.get("customer") or {}
    print(f"   客户: orders_count={cu.get('orders_count')} "
          f"email={cu.get('email', '')}")
    print(f"   referrer: {o.get('referring_site', '')}")
    print(f"   landing: {o.get('landing_site', '')}")
    for na in o.get("note_attributes", []) or []:
        print(f"   note_attr: {na.get('name')}={na.get('value')}")
    for li in o.get("line_items", []):
        print(f"   item: {li['title'][:70]} | {li.get('sku')} "
              f"x{li['quantity']} ${li['price']}")
        for pr in li.get("properties", []) or []:
            print(f"      prop: {pr.get('name')}={pr.get('value')}")

# ---------- 2. GA4 purchase 会话归因 ----------
at = httpx.post("https://oauth2.googleapis.com/token", data={
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "grant_type": "refresh_token"}, timeout=30).json()["access_token"]
H = {"Authorization": f"Bearer {at}", "Content-Type": "application/json"}


def runreport(body):
    r = httpx.post(
        f"https://analyticsdata.googleapis.com/v1beta/properties/{GA4}"
        ":runReport", headers=H, json=body, timeout=60)
    return r.json() if r.status_code == 200 else {"err": r.text[:200]}


print("\n=== 2. GA4 purchase 归因（11-14 起）===")
j = runreport({
    "dateRanges": [{"startDate": "2026-11-14", "endDate": "today"}],
    "dimensions": [{"name": "transactionId"}, {"name": "dateHour"},
                   {"name": "sessionSource"}, {"name": "sessionMedium"},
                   {"name": "sessionCampaignName"},
                   {"name": "sessionDefaultChannelGroup"},
                   {"name": "country"}, {"name": "deviceCategory"}],
    "metrics": [{"name": "eventCount"}, {"name": "purchaseRevenue"}],
    "dimensionFilter": {"filter": {
        "fieldName": "eventName",
        "stringFilter": {"value": "purchase"}}},
    "limit": 20})
if "rows" in j:
    for row in j["rows"]:
        d = [x["value"] for x in row["dimensionValues"]]
        m = [x["value"] for x in row["metricValues"]]
        print(f"  txn={d[0]} {d[1]} {d[2]}/{d[3]} camp={d[4][:40]} "
              f"{d[5]} {d[6]} {d[7]} ev={m[0]} rev=${m[1]}")
else:
    print(f"  (无数据或异常: {j.get('err', j.get('rowCount', 0))})")

# ---------- 3. Ads 近 3 日转化归属 ----------
print("\n=== 3. Ads 近 3 日各系列转化 ===")
gac = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True})
gas = gac.get_service("GoogleAdsService")
rows = gas.search(customer_id=CID, query=(
    "SELECT campaign.name, campaign.advertising_channel_type, "
    "metrics.clicks, metrics.cost_micros, metrics.conversions "
    "FROM campaign WHERE campaign.status='ENABLED' "
    "AND segments.date BETWEEN '2026-11-13' AND '2026-11-15'"))
for r in rows:
    m = r.metrics
    if m.conversions or m.clicks:
        print(f"  {r.campaign.name[:38]:<38} "
              f"{r.campaign.advertising_channel_type.name:<10} "
              f"clicks={m.clicks} ${m.cost_micros/1e6:.2f} "
              f"conv={m.conversions:.1f}")

print("\n=== 3b. 近 3 日搜索词（有点击）===")
try:
    rows = gas.search(customer_id=CID, query=(
        "SELECT search_term_view.search_term, campaign.name, "
        "metrics.clicks, metrics.cost_micros, metrics.conversions "
        "FROM search_term_view WHERE segments.date BETWEEN "
        "'2026-11-13' AND '2026-11-15'"))
    for r in rows:
        m = r.metrics
        if m.clicks:
            print(f"  {r.search_term_view.search_term[:38]:<38} "
                  f"{r.campaign.name[:28]:<28} "
                  f"clicks={m.clicks} ${m.cost_micros/1e6:.2f} "
                  f"conv={m.conversions:.1f}")
except Exception as e:
    print(f"  (search_term 查询失败: {str(e)[:120]})")

# ---------- 4. 今日干净口径验证 ----------
print("\n=== 4. 今日（11-16）付费流量国家 ===")
j = runreport({
    "dateRanges": [{"startDate": "today", "endDate": "today"}],
    "dimensions": [{"name": "country"}],
    "metrics": [{"name": "sessions"}],
    "dimensionFilter": {"filter": {
        "fieldName": "sessionDefaultChannelGroup",
        "inListFilter": {"values": ["Paid Search", "Paid Shopping",
                                    "Paid Video"]}}},
    "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
    "limit": 10})
if "rows" in j:
    for row in j["rows"]:
        print(f"  {row['dimensionValues'][0]['value']:<22} "
              f"{row['metricValues'][0]['value']}")
else:
    print(f"  (无数据或异常: {j.get('err', j.get('rowCount', 0))})")

print("\n=== 4b. 今日关键事件 ===")
j = runreport({
    "dateRanges": [{"startDate": "today", "endDate": "today"}],
    "dimensions": [{"name": "eventName"}],
    "metrics": [{"name": "eventCount"}],
    "dimensionFilter": {"filter": {
        "fieldName": "eventName",
        "inListFilter": {"values": ["add_to_cart", "generate_lead",
                                    "purchase", "begin_checkout"]}}}})
if "rows" in j:
    for row in j["rows"]:
        print(f"  {row['dimensionValues'][0]['value']:<22} "
              f"{row['metricValues'][0]['value']}")
else:
    print(f"  (无数据或异常: {j.get('err', j.get('rowCount', 0))})")
