# -*- coding: utf-8 -*-
"""PMax/Search 无效网址诊断 v5：
1) 两系列类型 + shopping_setting + PMax 全部资产组(含 REMOVED)
2) Search 广告 ad 级 final_urls（GAQL 可查）+ PMax 页面信息卡 asset_set
3) 每个 URL 提取 handle -> Shopify Admin API 核实存在性（不踩前台限流）"""
import os
import re
import sys
import time

sys.path.insert(0, "/home/jason/shopify-admin/src")
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

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


def rows(q):
    return list(gas.search(customer_id=CID, query=q))


print("=== 1) 系列概况 ===")
for r in rows(
    "SELECT campaign.id, campaign.name, campaign.advertising_channel_type, "
    "campaign.status, campaign.shopping_setting.merchant_id, "
    "campaign.shopping_setting.feed_label "
    "FROM campaign"
):
    c = r.campaign
    sh = c.shopping_setting
    print(f"  {c.id} {c.name[:32]:32} {c.advertising_channel_type.name:16} "
          f"{c.status.name:9} merchant={sh.merchant_id if sh else '-'} "
          f"feed={sh.feed_label if sh else '-'}")

print("\n=== 2) PMax 全部资产组（含 REMOVED）===")
for r in rows(
    "SELECT asset_group.id, asset_group.name, asset_group.status, "
    "asset_group.final_urls "
    f"FROM asset_group WHERE campaign.id = {PMAX}"
):
    g = r.asset_group
    print(f"  [{g.status.name:9}] {g.name[:36]:36} {g.final_urls}")

print("\n=== 3) PMax 页面信息卡 asset_set ===")
n_as = 0
for r in rows(
    "SELECT asset_set.id, asset_set.name, campaign_asset_set.status "
    f"FROM campaign_asset_set WHERE campaign.id = {PMAX}"
):
    a = r.asset_set
    n_as += 1
    print(f"  asset_set[{a.id}] {a.name[:40]} type={a.type_.name} "
          f"campaign_link={r.campaign_asset_set.status.name}")
    for r2 in rows(
        f'SELECT asset_set_asset.status, asset.resource_name, asset.name '
        f'FROM asset_set_asset WHERE asset_set_asset.asset_set = '
        f'"customers/{CID}/assetSets/{a.id}"'
    ):
        print(f"      {r2.asset_set_asset.status.name:9} "
              f"{r2.asset.name[:50]}")
if not n_as:
    print("  (无 page feed 资产集)")

print("\n=== 4) Search 广告 ad 级 final_urls ===")
urls = {}
for r in rows(
    "SELECT ad_group_ad.ad.name, ad_group_ad.ad.final_urls, "
    "ad_group_ad.status, ad_group_ad.policy_summary.approval_status "
    f"FROM ad_group_ad WHERE campaign.id = {SEARCH}"
):
    ad = r.ad_group_ad
    st = (ad.policy_summary.approval_status.name
          if ad.policy_summary else "-")
    for u in ad.ad.final_urls or []:
        urls.setdefault(u, []).append(
            f"{ad.ad.name[:30]}/{ad.status.name}/{st}")
    print(f"  ad[{ad.ad.name[:34]:34}] {ad.status.name:9} pol={st} "
          f"n_urls={len(ad.ad.final_urls or [])}")

print(f"\n=== 5) Admin API 核实 {len(urls)} 个 URL ===")
cl = ShopifyRest(StoreService().get_client(1))
# 缓存店 handle 集合
all_handles = {}
page = None
while True:
    batch = cl.products(250, page_info=page)
    if not batch:
        break
    for p in batch:
        all_handles[p["handle"]] = p["status"]
    page = cl._client.get(  # noqa 取下一页游标
        "products.json", params={"limit": 250}, auth=cl._auth
    ).links.get("next")
    if not page:
        break
print(f"  店内产品 handle 总数: {len(all_handles)} "
      f"(active={sum(1 for s in all_handles.values() if s=='active')})")

colls = {}
for fetch in (cl.custom_collections, cl.smart_collections):
    for c in fetch(250):
        colls[c["handle"]] = bool(c.get("published_at"))

bad = []
for u, srcs in urls.items():
    m = re.search(r"/products/([a-z0-9-]+)", u) or re.search(
        r"/collections/([a-z0-9-]+)", u)
    if not m:
        kind, h = "?", u
    else:
        h = m.group(1)
        kind = "product" if "/products/" in u else "collection"
    if kind == "product":
        st = all_handles.get(h)
        ok = st == "active"
        desc = f"status={st}"
    elif kind == "collection":
        ok = colls.get(h, False)
        desc = f"published={colls.get(h)}"
    else:
        ok, desc = None, "非产品/合集路径"
    print(f"  [{'OK' if ok else 'BAD' if ok is False else '??'}] {u[:80]} "
          f"<- {srcs[0][:40]} | {desc}")
    if ok is False:
        bad.append((u, srcs, desc))

print(f"\n=== 无效 URL {len(bad)} 个 ===")
for u, srcs, d in bad:
    print(f"  {u} | {d} | {srcs}")
