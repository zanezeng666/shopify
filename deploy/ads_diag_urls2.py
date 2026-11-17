# -*- coding: utf-8 -*-
"""PMax 诊断 v4：
A) Shopify Admin API 核实 /collections/medical-battery 是否存在 + 列可用合集
B) GAQL 真政策异常资产（DISAPPROVED 等才报，policy_summary 空不报）
C) campaign 级 3 资产类型"""
import os
import sys

sys.path.insert(0, "/home/jason/shopify-admin/src")
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient

from shopify_admin.platforms.shopify.rest import ShopifyRest
from shopify_admin.services.stores.service import StoreService

load_dotenv("/home/jason/shopify-admin/.env")
CID = "7059800494"
PMAX = 24441391608
BAD_STATUS = {"DISAPPROVED", "AREA_OF_INTEREST_ONLY",
              "CERTIFICATE_REQUIRED", "LIMITED"}

print("=== A) Shopify collection 核实 ===")
cl = ShopifyRest(StoreService().get_client(1))
allc = []
for fetch in (cl.custom_collections, cl.smart_collections):
    for it in fetch(250):
        allc.append(it)
print(f"  店内合集总数: {len(allc)}")
found = [c for c in allc if c.get("handle") == "medical-battery"]
if found:
    c = found[0]
    print(f"  >>> /collections/medical-battery 存在: "
          f"id={c['id']} title={c['title']!r} "
          f"published={c.get('published_at')}")
else:
    print("  >>> /collections/medical-battery 不存在 -> PMax 落地页 404 实锤")
    med = [c for c in allc if "medic" in (c.get("title", "") + c.get("handle", "")).lower()]
    print("  含 medic 的候选合集：")
    for c in med[:12]:
        print(f"    {c.get('handle'):42} {c.get('title', '')[:44]} "
              f"pub={bool(c.get('published_at'))}")

print("\n  published 合集（前 30）：")
seen = 0
for c in allc:
    if c.get("published_at"):
        seen += 1
        if seen <= 30:
            print(f"    {c.get('handle'):42} {c.get('title', '')[:40]}")
print(f"  (published 共 {seen}/{len(allc)})")

print("\n=== B) Google Ads 真政策异常资产 ===")
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


asset_rns = []
for tbl in ("campaign_asset", "asset_group_asset"):
    for r in rows(
        f"SELECT campaign.id, {tbl}.asset FROM {tbl} "
        f"WHERE campaign.id = {PMAX}"
    ):
        asset_rns.append(getattr(r, tbl).asset)
asset_rns = list(dict.fromkeys(asset_rns))
in_list = ", ".join(f'"{n}"' for n in asset_rns)
nbad = 0
for r in rows(
    "SELECT asset.resource_name, asset.name, asset.type, "
    "asset.policy_summary.approval_status, "
    "asset.policy_summary.policy_topic_entries "
    f"FROM asset WHERE asset.resource_name IN ({in_list})"
):
    a = r.asset
    st = (a.policy_summary.approval_status.name
          if a.policy_summary else "NO_POLICY_SUMMARY")
    if st in BAD_STATUS:
        nbad += 1
        ents = "; ".join(
            f"{e.type_}/{e.entry_type.name}" for e in
            (a.policy_summary.policy_topic_entries or []))
        print(f"  {st:16} {a.type.name:16} {a.name[:44]:44} {ents[:70]}")
print(f"  真政策异常: {nbad} 个（其余 policy_summary 空为正常未评估）")

print("\n=== C) campaign 级资产详情 ===")
CAMP = [437606222749, 437606222764, 437497818251]
cin = ", ".join(
    f'"customers/{CID}/assets/{i}"' for i in CAMP)
for r in rows(
    "SELECT asset.resource_name, asset.name, asset.type, "
    "asset.policy_summary.approval_status "
    f"FROM asset WHERE asset.resource_name IN ({cin})"
):
    a = r.asset
    st = (a.policy_summary.approval_status.name
          if a.policy_summary else "-")
    print(f"  {a.type.name:16} {st:14} {a.name[:50]} {a.resource_name}")
