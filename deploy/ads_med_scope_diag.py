# -*- coding: utf-8 -*-
"""医疗投放范围与广告内容一致性诊断。
A) 落地页 collection 构成与医疗类 product_type 值
B) PMax/Search 全部文本资产内容（查 Cameron Sino 残留等不一致）
C) listing_group_filter 可用字段元数据
"""
import os
import sys

from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

sys.path.insert(0, "/home/jason/shopify-admin/src")
from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
SEARCH = 24448362668

client = GoogleAdsClient.load_from_dict({
    "developer_token": "unused",
    "client_id": os.environ["GOOGLE_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
    "use_proto_plus": True,
})
gas = client.get_service("GoogleAdsService")
rows = lambda q: gas.search(customer_id=CID, query=q)  # noqa: E731

print("=== A) Shopify 医疗类构成 ===")
cl = ShopifyRest(StoreService().get_client(1))
# collection 159760384100 = medical-battery
med = None
for fetch in (cl.custom_collections, cl.smart_collections):
    for c in fetch(250):
        if c.get("id") == 159760384100:
            med = c
            kind = "custom"
            break
    if med:
        break
if med:
    print(f"  collection={med['id']} kind={kind} title={med['title']!r} "
          f"published={med.get('published_at')}")
    if kind == "smart":
        rules = med.get("rules", [])
        print(f"  smart 规则: "
              f"{[(r.get('column'), r.get('relation'), r.get('condition')) for r in rules]}")
else:
    print("  (未在两表找到该 collection)")

# published 产品 product_type 分布（找医疗值）
from collections import Counter  # noqa: E402

ptc = Counter()
med_types = Counter()
since = 0
while True:
    r = cl.client.request(
        "GET", "products.json",
        params={"limit": 250, "published_status": "published",
                "since_id": since, "fields": "id,product_type"},
    )
    items = r.get("products", [])
    if not items:
        break
    for p in items:
        t = p.get("product_type") or "(空)"
        ptc[t] += 1
        if "medic" in t.lower() or "patient" in t.lower() or "defib" in t.lower():
            med_types[t] += 1
    since = items[-1]["id"]
    if len(items) < 250:
        break
print(f"\n  published 总数={sum(ptc.values())}, product_type 种类={len(ptc)}")
print("  医疗相关 product_type:")
for t, n in med_types.most_common():
    print(f"    {t!r}: {n}")
print("  非医疗 top10:", ptc.most_common(10))

print("\n=== B) PMax 文本资产内容 ===")
try:
    rs = list(rows(
        "SELECT asset_group.name, asset_group_asset.field_type, "
        "asset_group_asset.status, asset.name, asset.text_asset.text "
        "FROM asset_group_asset WHERE campaign.id = " + str(PMAX)))
    for r in rs:
        aga = r.asset_group_asset
        txt = (r.asset.text_asset.text if r.asset.text_asset else "") or ""
        print(f"  [{aga.field_type.name:14}] {aga.status.name:9} "
              f"{txt[:80]!r}")
except Exception as e:  # noqa
    print(f"  查询失败: {str(e)[:300]}")

print("\n=== B2) Search 广告文本 ===")
try:
    rs = list(rows(
        "SELECT ad_group.name, ad_group_ad.status, "
        "ad_group_ad.ad.responsive_search_ad.headlines, "
        "ad_group_ad.ad.responsive_search_ad.descriptions, "
        "ad_group_ad.ad.final_urls "
        "FROM ad_group_ad WHERE campaign.id = " + str(SEARCH)))
    for r in rs:
        ad = r.ad_group_ad.ad
        hls = [h.ad_text_asset.text for h in
               (ad.responsive_search_ad.headlines or [])]
        dss = [d.ad_text_asset.text for d in
               (ad.responsive_search_ad.descriptions or [])]
        print(f"  [{r.ad_group.name[:24]}] {r.ad_group_ad.status.name} "
              f"url={ad.final_urls}")
        for h in hls:
            print(f"    H: {h!r}")
        for d in dss:
            print(f"    D: {d!r}")
except Exception as e:  # noqa
    print(f"  查询失败: {str(e)[:300]}")

print("\n=== C) listing_group_filter 字段元数据 ===")
try:
    rs = list(rows(
        "SELECT name, data_type, selectable FROM google_ads_field "
        "WHERE name LIKE 'asset_group_listing_group_filter%'"))
    for r in rs:
        print(f"  {r.google_ads_field.name:70} "
              f"{r.google_ads_field.data_type.name:10} "
              f"sel={r.google_ads_field.selectable}")
except Exception as e:  # noqa
    print(f"  失败: {str(e)[:300]}")
